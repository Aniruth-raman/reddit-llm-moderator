#!/usr/bin/env python3
"""
Shared Moderation Services for Reddit LLM Moderator.
"""

from typing import Dict, Any, Optional


class ModerationRule:
    """Represents a subreddit moderation rule."""

    def __init__(self, rule_data: Dict[str, Any]):
        """
        Initialize a moderation rule from a dictionary.
        
        Args:
            rule_data: Dictionary containing rule data
        """
        self.number = rule_data.get("number")
        self.title = rule_data.get("title", "")
        self.explanation = rule_data.get("explanation", "")
        self.response = rule_data.get("response", "")
        self.notification_method = rule_data.get("notification_method", "public")

    def __repr__(self):
        return f"Rule {self.number}: {self.title}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "explanation": self.explanation,
            "response": self.response,
            "notification_method": self.notification_method
        }


class ModerationDecision:
    """Represents a moderation decision made by an LLM."""

    def __init__(self, decision_data: Dict[str, Any]):
        """
        Initialize a moderation decision from a dictionary.
        
        Args:
            decision_data: Dictionary containing the decision data
        """
        self.violates = decision_data.get("violates", False)
        self.rule_number = decision_data.get("rule_number")
        self.explanation = decision_data.get("explanation", "No explanation provided")
        self.confidence = decision_data.get("confidence", 0.0)
        self.error = decision_data.get("error")

    def __repr__(self):
        if self.violates:
            return f"Violates Rule {self.rule_number}: {self.explanation} (confidence: {self.confidence:.2f})"
        elif self.error:
            return f"Error: {self.error}"
        else:
            return f"No violation (confidence: {self.confidence:.2f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        result = {
            "violates": self.violates,
            "confidence": self.confidence
        }

        if self.violates:
            result["rule_number"] = self.rule_number
            result["explanation"] = self.explanation

        if self.error:
            result["error"] = self.error

        return result


class ModerationResult:
    """Represents the result of a moderation action."""

    def __init__(
            self,
            item_id: str,
            item_type: str,
            action_taken: str,
            rule_number: Optional[int] = None,
            explanation: Optional[str] = None
    ):
        """
        Initialize a moderation result.
        
        Args:
            item_id: Reddit item ID
            item_type: Type of item ("submission" or "comment")
            action_taken: Action that was taken ("approved", "removed", etc.)
            rule_number: Rule number if removed
            explanation: Explanation if available
        """
        self.item_id = item_id
        self.item_type = item_type
        self.action_taken = action_taken
        self.rule_number = rule_number
        self.explanation = explanation

    def __repr__(self):
        if self.rule_number:
            return f"{self.item_type} {self.item_id}: {self.action_taken} (Rule {self.rule_number})"
        else:
            return f"{self.item_type} {self.item_id}: {self.action_taken}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        result = {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "action_taken": self.action_taken
        }

        if self.rule_number:
            result["rule_number"] = self.rule_number

        if self.explanation:
            result["explanation"] = self.explanation

        return result
