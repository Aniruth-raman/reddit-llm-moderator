#!/usr/bin/env python3
"""
Example client for the Reddit LLM Moderator MCP server.
"""

import json
import requests
import logging
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def main():
    """Example client for the MCP server."""
    parser = argparse.ArgumentParser(description="Reddit LLM Moderator MCP Client Example")
    parser.add_argument(
        "--server", default="http://localhost:8000", help="MCP server URL"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--rules", default="rules.yaml", help="Path to rules file"
    )
    parser.add_argument(
        "--subreddit", required=True, help="Subreddit to moderate"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't take any actions"
    )
    args = parser.parse_args()
    
    # Base URL for API requests
    api_url = args.server
    
    try:
        # Step 1: Initialize the server
        logger.info(f"Initializing server with config: {args.config} and rules: {args.rules}")
        init_response = requests.post(
            f"{api_url}/initialize",
            json={"config_path": args.config, "rules_path": args.rules}
        )
        init_response.raise_for_status()
        logger.info("Server initialized successfully")
        
        # Step 2: Get modqueue items
        logger.info(f"Fetching modqueue for r/{args.subreddit}")
        modqueue_response = requests.get(
            f"{api_url}/modqueue",
            params={"subreddit": args.subreddit, "limit": 10, "item_type": "all"}
        )
        modqueue_response.raise_for_status()
        
        modqueue_data = modqueue_response.json()
        items = modqueue_data.get("items", [])
        
        if not items:
            logger.info("Modqueue is empty")
            return
            
        logger.info(f"Found {len(items)} items in modqueue")
        
        # Step 3: Process each item
        for item in items:
            item_id = item["id"]
            item_type = item["type"]
            
            if item_type == "submission":
                identifier = item.get("title", "")
            else:
                identifier = item.get("body", "")[:50] + "..."
                
            logger.info(f"Processing {item_type}: {identifier}")
            
            # Step 4: Moderate the item
            moderate_response = requests.post(
                f"{api_url}/moderate",
                json={
                    "subreddit": args.subreddit,
                    "item_id": item_id,
                    "dry_run": args.dry_run,
                    "notification_method": "public"
                }
            )
            moderate_response.raise_for_status()
            
            result = moderate_response.json()
            action = result.get("result", {}).get("action_taken", "unknown")
            
            if action == "removed":
                rule_number = result.get("result", {}).get("rule_number", "unknown")
                logger.info(f"Result: Removed (Rule {rule_number})")
            else:
                logger.info(f"Result: {action.capitalize()}")
                
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
