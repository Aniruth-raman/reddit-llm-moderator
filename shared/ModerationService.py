from typing import List, Dict, Any

from shared.Moderation import ModerationDecision, ModerationResult
from shared.NotificationStrategy import PublicNotificationStrategy, ModmailNotificationStrategy, NotificationStrategy
from shared.RuleMatcher import RuleMatcher
from shared.utils import logger


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
            dry_run: bool = False,
            confidence_threshold: float = 0.8
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
            confidence_threshold: Minimum confidence required to take action

        Returns:
            ModerationResult indicating the action taken
        """
        # Determine item type
        is_submission = hasattr(item, "title")
        item_type = "submission" if is_submission else "comment"
        item_identifier = item.title if is_submission else item.body[:50] + "..."

        # Check confidence threshold - if confidence is too low, take no action
        if decision.confidence < confidence_threshold:
            logger.info(
                f"SKIPPING {item_type}: '{item_identifier}' - confidence {decision.confidence:.2f} below threshold {confidence_threshold}")

            return ModerationResult(
                item_id=item.id,
                item_type=item_type,
                action_taken="no_action",
                explanation=f"Confidence {decision.confidence:.2f} below threshold {confidence_threshold}"
            )

        # Handle cases where no violation is found but confidence is high enough
        if not decision.violates:
            logger.info(f"APPROVING {item_type}: '{item_identifier}' - confidence: {decision.confidence:.2f}")

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

        # Handle rule violations (with sufficient confidence)
        logger.info(f"REMOVING {item_type}: '{item_identifier}' - {rule} - confidence: {decision.confidence:.2f}")
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
