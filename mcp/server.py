#!/usr/bin/env python3
"""
MCP server implementation for Reddit LLM Moderator.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import shared components
from shared.LLMProvider import LLMProviderFactory
from shared.utils import create_llm_prompt, load_config, load_rules, authenticate_reddit, logger
from shared.Moderation import ModerationDecision, ModerationResult, ModerationRule
from shared.ModerationService import ModerationService

# Create FastAPI application
app = FastAPI(
    title="Reddit LLM Moderator API",
    description="API for moderating Reddit content using LLMs",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global application state
class AppState:
    """Application state class."""

    def __init__(self):
        """Initialize application state."""
        self.config = None
        self.rules = None
        self.reddit = None
        self.subreddits = {}
        self.moderation_service = ModerationService()


app_state = AppState()


# Pydantic models for API
class ConfigRequest(BaseModel):
    """Request model for configuration."""

    config_path: str = Field(default="config.yaml", description="Path to configuration file")
    rules_path: str = Field(default="rules.yaml", description="Path to rules file")


class ModerateRequest(BaseModel):
    """Request model for moderation."""

    subreddit: str = Field(..., description="Subreddit name")
    item_id: str = Field(..., description="Reddit item ID (submission or comment)")
    dry_run: bool = Field(default=True, description="If True, don't take any actions")
    notification_method: str = Field(default="public", description="Notification method (public or modmail)")


class ModQueueRequest(BaseModel):
    """Request model for fetching modqueue."""

    subreddit: str = Field(..., description="Subreddit name")
    limit: int = Field(default=100, description="Maximum number of items to fetch")
    item_type: str = Field(default="all", description="Type of items (all, submissions, comments)")


# Dependency to ensure application is initialized
async def get_app_state():
    """Get application state, initializing if needed."""
    if app_state.config is None:
        raise HTTPException(
            status_code=500,
            detail="Application not initialized. Call /initialize first."
        )
    return app_state


@app.post("/initialize")
async def initialize(request: ConfigRequest):
    """
    Initialize the application with config and rules.
    """
    try:
        # Load configuration
        config = load_config(request.config_path)
        if not config:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load config from: {request.config_path}"
            )

        # Load rules
        rules = load_rules(request.rules_path)
        if not rules:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load rules from: {request.rules_path}"
            )

        # Authenticate with Reddit
        reddit = authenticate_reddit(config["reddit"])

        # Update application state
        app_state.config = config
        app_state.rules = rules  # Keep as raw dicts for compatibility
        app_state.reddit = reddit

        # Log initialization details
        logger.info(f"Initialized with {len(rules)} rules")
        logger.info(f"Using LLM provider: {config.get('llm', {}).get('provider', 'openai')}")

        return {"status": "success", "message": "Application initialized"}

    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/modqueue")
async def get_modqueue(
        request: ModQueueRequest,
        app_state: AppState = Depends(get_app_state)
):
    """
    Get items from a subreddit's modqueue.
    """
    try:
        # Get or create subreddit instance
        if request.subreddit not in app_state.subreddits:
            app_state.subreddits[request.subreddit] = app_state.reddit.subreddit(request.subreddit)

        subreddit = app_state.subreddits[request.subreddit]

        # Fetch modqueue items
        modqueue_items = list(subreddit.mod.modqueue(limit=request.limit))
        logger.info(f"Found {len(modqueue_items)} items in r/{request.subreddit} modqueue")

        # Filter by type if needed
        if request.item_type != "all":
            is_submission_filter = (request.item_type == "submissions")
            modqueue_items = [
                item for item in modqueue_items
                if (hasattr(item, "title") == is_submission_filter)
            ]
            logger.info(f"Filtered to {len(modqueue_items)} {request.item_type}")

        # Convert items to dictionaries with better structure
        items = []
        for item in modqueue_items:
            is_submission = hasattr(item, "title")

            # Common properties
            item_dict = {
                "id": item.id,
                "type": "submission" if is_submission else "comment",
                "author": item.author.name if hasattr(item, "author") and item.author else "[deleted]",
                "created_utc": item.created_utc,
                "permalink": item.permalink if hasattr(item, "permalink") else "",
                "subreddit": item.subreddit.display_name
            }

            # Type-specific properties
            if is_submission:
                item_dict.update({
                    "title": item.title,
                    "selftext": item.selftext if hasattr(item, "selftext") else "",
                    "url": item.url if hasattr(item, "url") else "",
                    "domain": item.domain if hasattr(item, "domain") else "",
                    "score": item.score if hasattr(item, "score") else 0,
                    "num_reports": item.num_reports if hasattr(item, "num_reports") else 0
                })
            else:
                item_dict.update({
                    "body": item.body,
                    "link_title": item.link_title if hasattr(item, "link_title") else "",
                    "parent_id": item.parent_id if hasattr(item, "parent_id") else "",
                    "score": item.score if hasattr(item, "score") else 0
                })

            items.append(item_dict)

        return {"status": "success", "items": items, "count": len(items)}

    except Exception as e:
        logger.error(f"Modqueue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/moderate")
async def moderate_item(
        request: ModerateRequest,
        app_state: AppState = Depends(get_app_state)
):
    """
    Moderate a specific Reddit item.
    """
    try:
        # Get or create subreddit instance
        if request.subreddit not in app_state.subreddits:
            app_state.subreddits[request.subreddit] = app_state.reddit.subreddit(request.subreddit)

        subreddit = app_state.subreddits[request.subreddit]

        # Fetch the item (could be submission or comment)
        item = None

        # First try as submission
        try:
            item = app_state.reddit.submission(id=request.item_id)
        except Exception:
            # Then try as comment
            try:
                item = app_state.reddit.comment(id=request.item_id)
            except Exception:
                pass

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item not found: {request.item_id}"
            )

        # Get appropriate LLM config
        llm_config = app_state.config.get("llm", {}).copy()
        provider_name = llm_config.get("provider", "openai")
        provider_config = app_state.config.get(provider_name, {})
        llm_config.update(provider_config)

        # Create LLM provider
        llm_provider = LLMProviderFactory.create_provider(provider_name, provider_config)

        if not llm_provider:
            raise ValueError(f"Failed to create LLM provider: {provider_name}")

        # Create prompt and evaluate
        prompt = create_llm_prompt(item, app_state.rules)
        decision_data = llm_provider.evaluate_text(prompt)
        decision = ModerationDecision(decision_data)

        # Get confidence threshold from config
        confidence_threshold = app_state.config.get("llm", {}).get("confidence_threshold", 0.8)

        # Use the moderation service to handle the decision
        result = app_state.moderation_service.moderate_item(
            item=item,
            decision=decision,
            rules=app_state.rules,
            subreddit=subreddit,
            notification_method=request.notification_method,
            dry_run=request.dry_run,
            confidence_threshold=confidence_threshold
        )

        # Return the result
        return {
            "status": "success",
            "result": result.to_dict(),
            "decision": decision.to_dict(),
            "dry_run": request.dry_run
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Moderation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rules")
async def get_rules(app_state: AppState = Depends(get_app_state)):
    """
    Get the configured rules.
    """
    # Convert raw rule dictionaries to ModerationRule objects
    rules = [ModerationRule(rule).to_dict() for rule in app_state.rules]
    return {"status": "success", "rules": rules}


def start_server():
    """Start the MCP server."""
    import uvicorn
    uvicorn.run("mcp.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start_server()
