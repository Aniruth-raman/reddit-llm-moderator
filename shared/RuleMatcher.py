from typing import Union, List, Dict, Any, Optional

from shared.Moderation import ModerationRule
from shared.utils import logger


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
        logger.debug(rule_number)
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
