#!/usr/bin/env python3
"""Main orchestration for Reddit LLM Moderator - simple threshold-based moderation.
Follows SOLID principles with proper dependency injection and separation of concerns."""
import argparse
import logging
import os
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
        """Load configuration from YAML file or environment variable."""
        # Check if config is provided via environment variable
        config_env = os.getenv('REDDIT_CONFIG_YAML')
        if config_env:
            logger.info("📝 Loading configuration from environment variable")
            return yaml.safe_load(config_env)
        
        # Fallback to file loading
        logger.info(f"📝 Loading configuration from file: {config_path}")
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def load_rules(rules_path='rules.yaml'):
        """Load subreddit rules from YAML file or environment variable."""
        # Check if rules are provided via environment variable
        rules_env = os.getenv('REDDIT_RULES_YAML')
        if rules_env:
            logger.info("📝 Loading rules from environment variable")
            return yaml.safe_load(rules_env)['rules']
        
        # Fallback to file loading
        logger.info(f"📝 Loading rules from file: {rules_path}")
        with open(rules_path, 'r') as f:
            return yaml.safe_load(f)['rules']


class ModerationService:
    """Main moderation service following Single Responsibility Principle."""
    
    def __init__(self, reddit_client, llm_evaluator, config, dry_run=False, disable_remove=False):
        self.reddit = reddit_client
        self.evaluator = llm_evaluator
        self.approve_threshold = config.get('approve_threshold', 80)
        self.remove_threshold = config.get('remove_threshold', 70)
        self.subreddit_name = config['reddit']['subreddit']
        self.dry_run = dry_run
        self.disable_remove = disable_remove
    
    def process_modqueue(self, rules):
        """Process modqueue items with confidence-based thresholds."""
        items = fetch_modqueue_items(self.reddit, self.subreddit_name)
        logger.info(f"📥 Processing {len(items)} items from r/{self.subreddit_name}")
        logger.info(f"⚙️  Settings: approve≥{self.approve_threshold}%, remove≥{self.remove_threshold}%")
        logger.info("=" * 60)
        
        if not items:
            logger.info("🎉 No items in modqueue - all clear!")
            return
            
        for i, item in enumerate(items, 1):
            logger.info(f"[{i}/{len(items)}] Processing item...")
            self._process_item(item, rules)
            logger.info("")  # Add spacing between items
    
    def _get_item_details(self, item):
        """Extract meaningful details from Reddit item for logging."""
        try:
            # Determine if it's a submission or comment
            is_submission = hasattr(item, 'title')
            author = item.author.name if hasattr(item, 'author') and item.author else '[Deleted]'
            item_id = getattr(item, 'id', 'unknown')
            
            if is_submission:
                title = getattr(item, 'title', '[No title]')
                url = getattr(item, 'url', '')
                # Truncate title if too long
                display_title = (title[:60] + '...') if len(title) > 60 else title
                permalink = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') else url
                
                return {
                    'type': 'submission',
                    'display': f'"{display_title}" by u/{author}',
                    'id': item_id,
                    'link': permalink,
                    'full_title': title
                }
            else:
                body = getattr(item, 'body', '[No body]')
                # Truncate comment body for display
                display_body = (body[:80] + '...') if len(body) > 80 else body
                # Remove newlines for cleaner display
                display_body = display_body.replace('\n', ' ').replace('\r', ' ')
                permalink = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') else ''
                
                return {
                    'type': 'comment',
                    'display': f'Comment: "{display_body}" by u/{author}',
                    'id': item_id,
                    'link': permalink,
                    'full_body': body
                }
        except Exception as e:
            logger.debug(f"Error extracting item details: {e}")
            return {
                'type': 'unknown',
                'display': f'Item {getattr(item, "id", "unknown")}',
                'id': getattr(item, 'id', 'unknown'),
                'link': '',
                'error': str(e)
            }
    
    def _process_item(self, item, rules):
        """Process a single modqueue item."""
        decision = self.evaluator.evaluate(item, rules)
        confidence = decision.get('confidence', 0)
        violates = decision.get('violates', False)
        item_details = self._get_item_details(item)
        
        if violates and confidence >= self.remove_threshold:
            self._remove_item(item, decision, item_details)
        elif not violates and confidence >= self.approve_threshold:
            self._approve_item(item, confidence, item_details)
        else:
            logger.info(f"⏸️  SKIPPED (confidence: {confidence}%) - {item_details['display']}")
            logger.debug(f"   Link: {item_details['link']}")
    
    def _remove_item(self, item, decision, item_details):
        """Remove item with proper reason and detailed logging."""
        rule_num = decision.get('rule_number', 'Unknown')
        reason = decision.get('explanation', 'Rule violation')
        confidence = decision.get('confidence', 0)
        
        # Create formatted log message
        log_header = f"🚫 REMOVED (Rule {rule_num}, confidence: {confidence}%)"
        log_content = f"   Content: {item_details['display']}"
        log_reason = f"   Reason: {reason}"
        log_link = f"   Link: {item_details['link']}" if item_details['link'] else ""
        
        if self.dry_run:
            logger.info(f"🔍 [DRY RUN] Would remove (Rule {rule_num}, confidence: {confidence}%)")
            logger.info(f"   Content: {item_details['display']}")
            logger.info(f"   Reason: {reason}")
            if item_details['link']:
                logger.info(f"   Link: {item_details['link']}")
        elif self.disable_remove:
            logger.info(f"⏸️  [REMOVE DISABLED] Would remove (Rule {rule_num}, confidence: {confidence}%)")
            logger.info(f"   Content: {item_details['display']}")
            logger.info(f"   Reason: {reason}")
            if item_details['link']:
                logger.info(f"   Link: {item_details['link']}")
        else:
            # remove_item(item, f"Rule {rule_num}: {reason}")  # Line 139 - commented out when disable_remove is True
            remove_item(item, f"Rule {rule_num}: {reason}")
            logger.info(log_header)
            logger.info(log_content)
            logger.info(log_reason)
            if log_link:
                logger.info(log_link)
    
    def _approve_item(self, item, confidence, item_details):
        """Approve item with detailed logging."""
        log_header = f"✅ APPROVED (confidence: {confidence}%)"
        log_content = f"   Content: {item_details['display']}"
        log_link = f"   Link: {item_details['link']}" if item_details['link'] else ""
        
        if self.dry_run:
            logger.info(f"✨ [DRY RUN] Would approve (confidence: {confidence}%)")
            logger.info(f"   Content: {item_details['display']}")
            if item_details['link']:
                logger.info(f"   Link: {item_details['link']}")
        else:
            approve_item(item)
            logger.info(log_header)
            logger.info(log_content)
            if log_link:
                logger.info(log_link)


def setup_logging(debug=False, log_file=None):
    """Setup logging configuration with improved formatting."""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Enhanced log format with better structure
    console_format = '%(asctime)s | %(levelname)-5s | %(message)s'
    file_format = '%(asctime)s | %(name)s | %(levelname)-5s | %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=file_format,
        handlers=[]
    )
    
    # Add console handler with simplified format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(console_format, datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    logging.getLogger().addHandler(console_handler)
    
    # Add file handler if specified with detailed format
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(file_handler)
        logger.info(f"📝 Logging to file: {log_file}")
        
    # Add separator for cleaner output
    logger.info("=" * 60)


def main():
    """Main application entry point following Dependency Inversion Principle."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Reddit LLM Moderator')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry-run mode (show suggestions without taking action)')
    parser.add_argument('--disable-remove', action='store_true',
                       help='Disable remove actions (equivalent to commenting out line 139)')
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
    
    logger.info("🤖 Reddit LLM Moderator Starting")
    if args.dry_run:
        logger.info("🔍 DRY RUN Mode - No actions will be taken")
    if args.disable_remove:
        logger.info("⏸️  REMOVE DISABLED Mode - Remove actions are disabled")
    logger.info("=" * 60)
    
    # Load configuration and rules
    config = ConfigManager.load_config(args.config)
    rules = ConfigManager.load_rules(args.rules)
    
    logger.debug(f"Loaded {len(rules)} rules")
    
    # Initialize dependencies
    reddit = create_reddit_client(config)
    evaluator = get_llm_evaluator(config)
    
    # Create and run moderation service
    moderation_service = ModerationService(reddit, evaluator, config, 
                                         dry_run=args.dry_run, 
                                         disable_remove=args.disable_remove)
    moderation_service.process_modqueue(rules)


if __name__ == "__main__":
    main()
