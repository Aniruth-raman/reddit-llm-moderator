#!/usr/bin/env python3
"""Main orchestration for Reddit LLM Moderator - simple threshold-based moderation."""
import yaml
from reddit_ops import create_reddit_client, fetch_modqueue_items, approve_item, remove_item
from llm_eval import get_llm_evaluator

def load_config(config_path='config.yaml'):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_rules(rules_path='rules.yaml'):
    """Load subreddit rules from YAML file."""
    with open(rules_path, 'r') as f:
        return yaml.safe_load(f)['rules']

def main():
    """Main moderation loop with confidence-based thresholds."""
    config = load_config()
    rules = load_rules()
    
    # Initialize Reddit client and LLM evaluator
    reddit = create_reddit_client(config)
    evaluator = get_llm_evaluator(config)
    
    # Get thresholds from config
    approve_threshold = config.get('approve_threshold', 80)
    remove_threshold = config.get('remove_threshold', 70)
    subreddit_name = config['reddit']['subreddit']
    
    # Process modqueue items
    items = fetch_modqueue_items(reddit, subreddit_name)
    print(f"Processing {len(items)} items from r/{subreddit_name}")
    
    for item in items:
        content = item.title if hasattr(item, 'title') else item.body
        confidence = evaluator.evaluate(content, rules)
        
        if confidence >= approve_threshold:
            approve_item(item)
            print(f"✓ Approved (confidence: {confidence}%)")
        elif confidence <= remove_threshold:
            remove_item(item)
            print(f"✗ Removed (confidence: {confidence}%)")
        else:
            print(f"? Skipped (confidence: {confidence}%)")

if __name__ == "__main__":
    main()
