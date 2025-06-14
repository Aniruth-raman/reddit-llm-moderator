#!/usr/bin/env python3
"""
Command-line interface for Reddit LLM Moderator.
"""

import argparse
import logging
import sys

# Import shared components
from shared.llm_core import LLMProviderFactory
from shared.utils import create_llm_prompt, load_config, load_rules, authenticate_reddit
from shared.models import ModerationDecision
from shared.moderation import ModerationService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def evaluate_item(item, rules, config):
    """
    Evaluate a Reddit item (submission or comment) against rules using the configured LLM provider.
    
    Args:
        item: Reddit item (submission or comment)
        rules: List of rule dictionaries
        config: LLM configuration dictionary
        
    Returns:
        ModerationDecision containing the evaluation result
    """
    try:
        # Determine which provider to use (default to openai if not specified)
        provider_name = config.get("provider", "openai")
        provider_config = config.get(provider_name, {"api_key": config.get("api_key")})
        
        # Create provider
        llm_provider = LLMProviderFactory.create_provider(provider_name, provider_config)
        
        if llm_provider:
            # Create prompt and evaluate
            prompt = create_llm_prompt(item, rules)
            decision_data = llm_provider.evaluate_text(prompt)
            return ModerationDecision(decision_data)
        else:
            raise ValueError(f"Failed to create LLM provider: {provider_name}")
                
    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}")
        return ModerationDecision({"violates": False, "error": str(e)})


def moderate_item(item, decision, rules, subreddit, dry_run=False, notification_method="public"):
    """
    Take moderation action on a Reddit item (submission or comment) based on LLM decision.
    
    Args:
        item: Reddit item (submission or comment)
        decision: ModerationDecision containing the LLM decision
        rules: List of rule dictionaries
        subreddit: The subreddit instance
        dry_run: If True, don't actually perform actions
        notification_method: How to notify users ("public" or "modmail")
        
    Returns:
        String describing the action taken
    """
    # Use the shared ModerationService
    moderation_service = ModerationService()
    
    # Let the service handle the moderation
    result = moderation_service.moderate_item(
        item=item,
        decision=decision,
        rules=rules,
        subreddit=subreddit,
        notification_method=notification_method,
        dry_run=dry_run
    )
    
    # Return a descriptive string of the action taken
    if result.action_taken == "approved":
        return "Approved"
    elif result.action_taken == "removed":
        if result.rule_number:
            return f"Removed (Rule {result.rule_number})"
        else:
            return "Removed"
    else:
        return f"Not actioned ({result.explanation})"


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Reddit LLM Moderator")
    parser.add_argument(
        "--subreddit", "-s", required=True, help="Subreddit to moderate"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Simulate actions without taking them",
    )
    parser.add_argument(
        "--config", "-c", default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--rules", "-r", default="rules.yaml", help="Path to rules file"
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "submissions", "comments"],
        default="all",
        help="Type of modqueue items to process: 'all', 'submissions', or 'comments'",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging for troubleshooting"
    )
    parser.add_argument(
        "--notification",
        choices=["public", "modmail"],
        default="public",
        help="How to deliver removal reasons: 'public' (comments/replies) or 'modmail'",
    )
    args = parser.parse_args()
    
    # Set logging level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Load configuration and rules
    config = load_config(args.config)
    rules = load_rules(args.rules)

    if not rules:
        logger.error("No rules found in the rules file")
        sys.exit(1)

    # Authenticate with Reddit
    reddit = authenticate_reddit(config["reddit"])

    # Log into which mode we're running
    mode = "DRY RUN (no actions will be taken)" if args.dry_run else "ACTIVE MODE"
    logger.info(f"Starting Reddit moderation in {mode}")
    logger.info(f"Target subreddit: r/{args.subreddit}")
    logger.info(f"Notification method: {args.notification}")

    try:
        # Get subreddit instance
        subreddit = reddit.subreddit(args.subreddit)

        # Fetch modqueue items (up to 100)
        modqueue_items = list(subreddit.mod.modqueue(limit=100))

        if not modqueue_items:
            logger.info("Modqueue is empty. No items to process.")
            return

        logger.info(f"Found {len(modqueue_items)} items in modqueue")
        
        # Log item type filter if specified
        if args.type != "all":
            logger.info(f"Filtering for {args.type} only")
            
        # Process each item in the modqueue
        for item in modqueue_items:
            # Determine if it's a submission or comment
            is_submission = hasattr(item, "title")
            item_type = "submission" if is_submission else "comment"
            
            # Skip items based on the type filter
            if args.type == "submissions" and not is_submission:
                continue
            if args.type == "comments" and is_submission:
                continue
                
            # Get a readable identifier for the item
            item_identifier = item.title if is_submission else item.body[:50] + "..."
            
            logger.info(f"Processing {item_type}: '{item_identifier}'")
            
            # Prepare LLM config by combining provider info with specific provider settings
            llm_config = config.get("llm", {}).copy()
            provider_name = llm_config.get("provider", "openai")
            provider_config = config.get(provider_name, {})
            llm_config.update(provider_config)
              # Evaluate item using LLM
            decision = evaluate_item(item, rules, llm_config)
            
            # Take moderation action
            result = moderate_item(
                item, 
                decision, 
                rules,
                subreddit,  # Pass the subreddit instance
                dry_run=args.dry_run,
                notification_method=args.notification
            )

    except KeyboardInterrupt:
        logger.info("Moderation stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
