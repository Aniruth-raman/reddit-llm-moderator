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
        decision = evaluator.evaluate(item, rules)
        confidence = decision.get('confidence', 0)
        violates = decision.get('violates', False)
        
        if violates and confidence >= remove_threshold:
            rule_num = decision.get('rule_number', 'Unknown')
            reason = decision.get('explanation', 'Rule violation')
            remove_item(item, f"Rule {rule_num}: {reason}")
            print(f"✗ Removed (Rule {rule_num}, confidence: {confidence}%)")
        elif not violates and confidence >= approve_threshold:
            approve_item(item)
            print(f"✓ Approved (confidence: {confidence}%)")
        else:
            print(f"? Skipped (confidence: {confidence}%)")

if __name__ == "__main__":
    main()
