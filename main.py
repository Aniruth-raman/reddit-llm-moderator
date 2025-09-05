#!/usr/bin/env python3
"""Main orchestration for Reddit LLM Moderator - simple threshold-based moderation.
Follows SOLID principles with proper dependency injection and separation of concerns."""
import yaml
from reddit_ops import create_reddit_client, fetch_modqueue_items, approve_item, remove_item
from llm_eval import get_llm_evaluator


class ConfigManager:
    """Handles configuration loading following Single Responsibility Principle."""
    
    @staticmethod
    def load_config(config_path='config.yaml'):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def load_rules(rules_path='rules.yaml'):
        """Load subreddit rules from YAML file."""
        with open(rules_path, 'r') as f:
            return yaml.safe_load(f)['rules']


class ModerationService:
    """Main moderation service following Single Responsibility Principle."""
    
    def __init__(self, reddit_client, llm_evaluator, config):
        self.reddit = reddit_client
        self.evaluator = llm_evaluator
        self.approve_threshold = config.get('approve_threshold', 80)
        self.remove_threshold = config.get('remove_threshold', 70)
        self.subreddit_name = config['reddit']['subreddit']
    
    def process_modqueue(self, rules):
        """Process modqueue items with confidence-based thresholds."""
        items = fetch_modqueue_items(self.reddit, self.subreddit_name)
        print(f"Processing {len(items)} items from r/{self.subreddit_name}")
        
        for item in items:
            self._process_item(item, rules)
    
    def _process_item(self, item, rules):
        """Process a single modqueue item."""
        decision = self.evaluator.evaluate(item, rules)
        confidence = decision.get('confidence', 0)
        violates = decision.get('violates', False)
        
        if violates and confidence >= self.remove_threshold:
            self._remove_item(item, decision)
        elif not violates and confidence >= self.approve_threshold:
            self._approve_item(item, confidence)
        else:
            print(f"? Skipped (confidence: {confidence}%)")
    
    def _remove_item(self, item, decision):
        """Remove item with proper reason."""
        rule_num = decision.get('rule_number', 'Unknown')
        reason = decision.get('explanation', 'Rule violation')
        remove_item(item, f"Rule {rule_num}: {reason}")
        print(f"✗ Removed (Rule {rule_num}, confidence: {decision.get('confidence', 0)}%)")
    
    def _approve_item(self, item, confidence):
        """Approve item."""
        approve_item(item)
        print(f"✓ Approved (confidence: {confidence}%)")


def main():
    """Main application entry point following Dependency Inversion Principle."""
    # Load configuration and rules
    config = ConfigManager.load_config()
    rules = ConfigManager.load_rules()
    
    # Initialize dependencies
    reddit = create_reddit_client(config)
    evaluator = get_llm_evaluator(config)
    
    # Create and run moderation service
    moderation_service = ModerationService(reddit, evaluator, config)
    moderation_service.process_modqueue(rules)


if __name__ == "__main__":
    main()
