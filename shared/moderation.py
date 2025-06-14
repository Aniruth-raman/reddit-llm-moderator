#!/usr/bin/env python3
"""
Shared moderation service for Reddit LLM Moderator.
"""

import logging
from typing import Dict, Any, List, Optional, Union

# Import shared models
from shared.models import ModerationRule, ModerationDecision, ModerationResult

logger = logging.getLogger(__name__)

class NotificationStrategy:
    """Base class for notification strategies."""
    
    def notify(self, item, rule: ModerationRule, subreddit) -> None:
        """Send notification for a removed item."""
        pass


class PublicNotificationStrategy(NotificationStrategy):
    """Strategy for public notifications."""
    
    def notify(self, item, rule: ModerationRule, subreddit) -> None:
        """Send a public notification via comment or removal message."""
        is_submission = hasattr(item, "title")
        response_text = rule.response
        
        if is_submission:
            item.mod.send_removal_message(response_text, type="public")
        else:
            try:
                item.reply(response_text)
            except Exception as e:
                logger.warning(f"Could not reply to comment: {e}")


class ModmailNotificationStrategy(NotificationStrategy):
    """Strategy for modmail notifications."""
    
    def notify(self, item, rule: ModerationRule, subreddit) -> None:
        """Send a notification via modmail."""
        is_submission = hasattr(item, "title")
        response_text = rule.response
        
        try:
            # For both submissions and comments
            author = item.author
            if author:  # Ensure author exists (not deleted)
                # Create subject line
                subject = f"Post Removal from r/{subreddit.display_name}"
                
                # Compose modmail message
                message_body = f"{response_text}\n\n"
                
                if is_submission:
                    message_body += f"Your post titled: '{item.title}' was removed."
                else:
                    # For comments, include part of the comment and link to parent
                    message_body += f"Your comment: '{item.body[:100]}...' was removed."
                
                # Send the modmail
                author.message(subject, message_body, from_subreddit=subreddit)
                logger.info(f"Sent removal reason via modmail to u/{author.name}")
        except Exception as e:
            logger.warning(f"Could not send modmail: {e}")


class RuleMatcher:
    """Helper class for finding matching rules."""
    
    @staticmethod
    def find_matching_rule(rule_number: Union[int, str], rules: List[Dict[str, Any]]) -> Optional[ModerationRule]:
        """
        Find a matching rule, handling type conversions as needed.
        
        Args:
            rule_number: The rule number to find (can be int or string)
            rules: List of rule dictionaries
            
        Returns:
            ModerationRule if found, None otherwise
        """
        # Direct match first
        rule_dict = next((r for r in rules if r["number"] == rule_number), None)
        
        # Try type conversion if no direct match
        if not rule_dict:
            if isinstance(rule_number, int):
                # Try matching with string
                rule_dict = next((r for r in rules if r["number"] == str(rule_number)), None)
            elif isinstance(rule_number, str) and rule_number.isdigit():
                # Try matching with int
                rule_dict = next((r for r in rules if r["number"] == int(rule_number)), None)
        
        # Create ModerationRule if found
        if rule_dict:
            return ModerationRule(rule_dict)
        
        return None


class ModerationService:
    """Service for handling content moderation."""
    
    def __init__(self):
        """Initialize the moderation service."""
        self.notification_strategies = {
            "public": PublicNotificationStrategy(),
            "modmail": ModmailNotificationStrategy()
        }
    
    def get_notification_strategy(self, method: str) -> NotificationStrategy:
        """Get the appropriate notification strategy."""
        return self.notification_strategies.get(method, self.notification_strategies["public"])
    
    def moderate_item(
        self, 
        item, 
        decision: ModerationDecision,
        rules: List[Dict[str, Any]],
        subreddit,
        notification_method: str = "public",
        dry_run: bool = False
    ) -> ModerationResult:
        """
        Moderate a Reddit item based on an LLM decision.
        
        Args:
            item: Reddit item (submission or comment)
            decision: LLM decision
            rules: List of rule dictionaries
            subreddit: Subreddit instance
            notification_method: How to notify users
            dry_run: If True, don't actually perform actions
            
        Returns:
            ModerationResult indicating the action taken
        """
        # Determine item type
        is_submission = hasattr(item, "title")
        item_type = "submission" if is_submission else "comment"
        item_identifier = item.title if is_submission else item.body[:50] + "..."
        
        # Handle cases where no violation is found
        if not decision.violates:
            logger.info(f"APPROVING {item_type}: '{item_identifier}'")
            
            if not dry_run:
                item.mod.approve()
                
            return ModerationResult(
                item_id=item.id,
                item_type=item_type,
                action_taken="approved"
            )
        
        # Find the rule that was violated
        rule = RuleMatcher.find_matching_rule(decision.rule_number, rules)
        
        # Handle cases where the rule isn't found
        if not rule:
            logger.warning(
                f"Rule {decision.rule_number} not found in rules configuration"
            )
            return ModerationResult(
                item_id=item.id,
                item_type=item_type,
                action_taken="no_action",
                explanation="Rule not found"
            )
        
        # Handle rule violations
        logger.info(f"REMOVING {item_type}: '{item_identifier}' - {rule}")
        logger.info(f"Explanation: {decision.explanation}")
        
        if not dry_run:
            # Remove the item
            item.mod.remove()
            
            # Notify using the appropriate strategy
            strategy = self.get_notification_strategy(notification_method)
            strategy.notify(item, rule, subreddit)
        
        # Return the result
        return ModerationResult(
            item_id=item.id,
            item_type=item_type,
            action_taken="removed",
            rule_number=decision.rule_number,
            explanation=decision.explanation
        )
