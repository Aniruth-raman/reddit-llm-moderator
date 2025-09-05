#!/usr/bin/env python3
"""Main orchestration for Reddit LLM Moderator - simple threshold-based moderation.
Follows SOLID principles with proper dependency injection and separation of concerns."""
import argparse
import logging
import sys
import yaml
from reddit_ops import create_reddit_client, fetch_modqueue_items, approve_item, remove_item
from llm_eval import get_llm_evaluator

# Configure logging
logger = logging.getLogger(__name__)


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
    
    def __init__(self, reddit_client, llm_evaluator, config, dry_run=False):
        self.reddit = reddit_client
        self.evaluator = llm_evaluator
        self.approve_threshold = config.get('approve_threshold', 80)
        self.remove_threshold = config.get('remove_threshold', 70)
        self.subreddit_name = config['reddit']['subreddit']
        self.dry_run = dry_run
    
    def process_modqueue(self, rules):
        """Process modqueue items with confidence-based thresholds."""
        items = fetch_modqueue_items(self.reddit, self.subreddit_name)
        logger.info(f"Processing {len(items)} items from r/{self.subreddit_name} (dry_run={self.dry_run})")
        
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
            logger.info(f"? Skipped (confidence: {confidence}%)")
    
    def _remove_item(self, item, decision):
        """Remove item with proper reason."""
        rule_num = decision.get('rule_number', 'Unknown')
        reason = decision.get('explanation', 'Rule violation')
        confidence = decision.get('confidence', 0)
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would remove (Rule {rule_num}, confidence: {confidence}%): {reason}")
        else:
            remove_item(item, f"Rule {rule_num}: {reason}")
            logger.info(f"✗ Removed (Rule {rule_num}, confidence: {confidence}%)")
    
    def _approve_item(self, item, confidence):
        """Approve item."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would approve (confidence: {confidence}%)")
        else:
            approve_item(item)
            logger.info(f"✓ Approved (confidence: {confidence}%)")


def setup_logging(debug=False, log_file=None):
    """Setup logging configuration."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[]
    )
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logging.getLogger().addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")


def main():
    """Main application entry point following Dependency Inversion Principle."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Reddit LLM Moderator')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry-run mode (show suggestions without taking action)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--log-file', type=str,
                       help='Log to specified file')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Configuration file path (default: config.yaml)')
    parser.add_argument('--rules', type=str, default='rules.yaml',
                       help='Rules file path (default: rules.yaml)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug=args.debug, log_file=args.log_file)
    
    logger.info("Starting Reddit LLM Moderator")
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no actions will be taken")
    
    # Load configuration and rules
    config = ConfigManager.load_config(args.config)
    rules = ConfigManager.load_rules(args.rules)
    
    logger.debug(f"Loaded {len(rules)} rules")
    
    # Initialize dependencies
    reddit = create_reddit_client(config)
    evaluator = get_llm_evaluator(config)
    
    # Create and run moderation service
    moderation_service = ModerationService(reddit, evaluator, config, dry_run=args.dry_run)
    moderation_service.process_modqueue(rules)


if __name__ == "__main__":
    main()
