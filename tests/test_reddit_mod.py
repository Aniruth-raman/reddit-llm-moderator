#!/usr/bin/env python3
"""
Test script for the Reddit Moderation CLI Tool.
Tests the shared moderation functionality including confidence thresholds.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from shared.utils import create_llm_prompt
from shared.Moderation import ModerationDecision, ModerationRule
from shared.ModerationService import ModerationService


class TestRedditMod(unittest.TestCase):
    """Test cases for Reddit moderation functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.rules = [
            {
                "number": 1,
                "title": "No spam",
                "explanation": "No spam allowed",
                "response": "Removed for spam"
            },
            {
                "number": 2,
                "title": "Be civil",
                "explanation": "Be civil to others",
                "response": "Removed for incivility"
            }
        ]
        
        # Mock submission
        self.submission = MagicMock()
        self.submission.id = "test123"
        self.submission.title = "Test Post"
        self.submission.selftext = "Test content"
        self.submission.url = "https://example.com"
        self.submission.domain = "example.com"
        
        # Mock subreddit
        self.subreddit = MagicMock()
        
        # Moderation service
        self.moderation_service = ModerationService()

    def test_create_llm_prompt(self):
        """Test creating LLM prompt"""
        prompt = create_llm_prompt(self.submission, self.rules)
        
        # Check that the prompt contains rule information
        self.assertIn("Rule 1: No spam", prompt)
        self.assertIn("Rule 2: Be civil", prompt)
        
        # Check that the prompt contains submission information
        self.assertIn("Title: Test Post", prompt)
        self.assertIn("Body: Test content", prompt)
        self.assertIn("URL: https://example.com", prompt)
        self.assertIn("Domain: example.com", prompt)
        
        # Check that confidence score is requested
        self.assertIn("confidence", prompt)

    def test_moderation_decision_model(self):
        """Test ModerationDecision model"""
        # Test no violation decision
        decision_data = {"violates": False, "confidence": 0.9}
        decision = ModerationDecision(decision_data)
        
        self.assertFalse(decision.violates)
        self.assertEqual(decision.confidence, 0.9)
        self.assertIsNone(decision.rule_number)
        
        # Test violation decision
        decision_data = {
            "violates": True, 
            "rule_number": 1, 
            "explanation": "This is spam",
            "confidence": 0.95
        }
        decision = ModerationDecision(decision_data)
        
        self.assertTrue(decision.violates)
        self.assertEqual(decision.rule_number, 1)
        self.assertEqual(decision.explanation, "This is spam")
        self.assertEqual(decision.confidence, 0.95)

    def test_high_confidence_approval(self):
        """Test approving with high confidence"""
        decision = ModerationDecision({"violates": False, "confidence": 0.9})
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "approved")
        self.assertEqual(result.item_id, "test123")

    def test_low_confidence_no_action(self):
        """Test no action with low confidence"""
        decision = ModerationDecision({"violates": False, "confidence": 0.6})
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "no_action")
        self.assertIn("confidence", result.explanation)

    def test_high_confidence_removal(self):
        """Test removing with high confidence"""
        decision = ModerationDecision({
            "violates": True,
            "rule_number": 1,
            "explanation": "This is spam",
            "confidence": 0.95
        })
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "removed")
        self.assertEqual(result.rule_number, 1)

    def test_low_confidence_violation_no_action(self):
        """Test no action for low confidence violation"""
        decision = ModerationDecision({
            "violates": True,
            "rule_number": 1,
            "explanation": "Maybe spam",
            "confidence": 0.5
        })
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "no_action")
        self.assertIn("confidence", result.explanation)

    def test_confidence_threshold_boundary(self):
        """Test confidence threshold boundary conditions"""
        # Exactly at threshold - should take action
        decision = ModerationDecision({"violates": False, "confidence": 0.8})
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "approved")
        
        # Just below threshold - should not take action
        decision = ModerationDecision({"violates": False, "confidence": 0.79})
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "no_action")

    def test_rule_not_found(self):
        """Test handling of unknown rule numbers"""
        decision = ModerationDecision({
            "violates": True,
            "rule_number": 999,
            "explanation": "Unknown rule",
            "confidence": 0.9
        })
        
        result = self.moderation_service.moderate_item(
            item=self.submission,
            decision=decision,
            rules=self.rules,
            subreddit=self.subreddit,
            dry_run=True,
            confidence_threshold=0.8
        )
        
        self.assertEqual(result.action_taken, "no_action")
        self.assertIn("Rule not found", result.explanation)


if __name__ == "__main__":
    unittest.main()
