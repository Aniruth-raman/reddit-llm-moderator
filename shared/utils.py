#!/usr/bin/env python3
"""
Shared utilities for Reddit LLM Moderator.
"""

import logging
import os
import sys
import yaml

logger = logging.getLogger(__name__)


def load_config(config_path):
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the config YAML file
        
    Returns:
        Dict containing configuration values
    """
    try:
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            return {}
            
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def load_rules(rules_path):
    """
    Load subreddit rules from a YAML file.
    
    Args:
        rules_path: Path to the rules YAML file
        
    Returns:
        List of rule dictionaries
    """
    try:
        if not os.path.exists(rules_path):
            logger.error(f"Rules file not found: {rules_path}")
            return []
            
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_data = yaml.safe_load(f)
        
        if not rules_data or "rules" not in rules_data:
            logger.error("Invalid rules file format")
            return []
            
        return rules_data["rules"]
    except Exception as e:
        logger.error(f"Failed to load rules: {e}")
        return []
        

def authenticate_reddit(reddit_config):
    """
    Authenticate with Reddit API.
    
    Args:
        reddit_config: Dictionary containing Reddit API credentials
        
    Returns:
        PRAW Reddit instance
    """
    try:
        import praw
        
        reddit = praw.Reddit(
            client_id=reddit_config.get("client_id"),
            client_secret=reddit_config.get("client_secret"),
            username=reddit_config.get("username"),
            password=reddit_config.get("password"),
            user_agent=reddit_config.get("user_agent")
        )
        
        # Verify credentials by checking username
        username = reddit.user.me().name
        logger.info(f"Authenticated as: {username}")
        
        return reddit
    except Exception as e:
        logger.error(f"Reddit authentication failed: {e}")
        sys.exit(1)

# Utility functions for prompt creation
def create_llm_prompt(item, rules):
    """Create a prompt for the LLM to evaluate a Reddit item (submission or comment) against rules."""
    rules_text = "\n".join(
        [
            f"Rule {rule['number']}: {rule['title']}\n"
            f"Explanation: {rule['explanation']}"
            for rule in rules
        ]
    )

    # Determine if the item is a submission or comment
    is_submission = hasattr(item, 'title')

    if is_submission:
        # Handle submission
        content_type = "submission"
        content_info = f"""SUBMISSION:
Title: {item.title}
Body: {item.selftext if hasattr(item, 'selftext') else '[No text content]'}
URL: {item.url if hasattr(item, 'url') else '[No URL]'}
Domain: {item.domain if hasattr(item, 'domain') else '[No domain]'}"""
    else:
        # Handle comment
        content_type = "comment"
        content_info = f"""COMMENT:
Body: {item.body}
Subreddit: {item.subreddit.display_name}
Link title: {item.link_title if hasattr(item, 'link_title') else '[Unknown]'}
Author: {item.author.name if hasattr(item, 'author') and item.author else '[Deleted]'}"""

    prompt = f"""
You are a Reddit moderator. Evaluate the following {content_type} against the subreddit's rules.
Respond with a JSON object containing your moderation decision.

SUBREDDIT RULES:
{rules_text}

{content_info}

If the {content_type} violates any rule, respond with:
{{
  "violates": true,
  "rule_number": [rule number],
  "explanation": "[your explanation why it violates this rule]"
}}

If the {content_type} does not violate any rule, respond with:
{{
  "violates": false
}}

Respond ONLY with the JSON object, nothing else.
"""
    return prompt
