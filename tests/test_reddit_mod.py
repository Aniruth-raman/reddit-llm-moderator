#!/usr/bin/env python3
"""
Test script for the Reddit Moderation CLI Tool.
This runs a simple test to validate rule processing.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import reddit_mod


class TestRedditMod(unittest.TestCase):
    """Test cases for reddit_mod.py"""

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
        self.submission.title = "Test Post"
        self.submission.selftext = "Test content"
        self.submission.url = "https://example.com"
        self.submission.domain = "example.com"

    def test_create_llm_prompt(self):
        """Test creating LLM prompt"""
        prompt = reddit_mod.create_llm_prompt(self.submission, self.rules)
        
        # Check that the prompt contains rule information
        self.assertIn("Rule 1: No spam", prompt)
        self.assertIn("Rule 2: Be civil", prompt)
        
        # Check that the prompt contains submission information
        self.assertIn("Title: Test Post", prompt)
        self.assertIn("Body: Test content", prompt)
        self.assertIn("URL: https://example.com", prompt)
        self.assertIn("Domain: example.com", prompt)

    @patch('reddit_mod.logger')
    def test_moderate_submission_approve(self, mock_logger):
        """Test approving a submission"""
        decision = {"violates": False}
        
        result = reddit_mod.moderate_submission(self.submission, decision, self.rules)
        
        self.assertEqual(result, "Approved")
        self.submission.mod.approve.assert_called_once()
        mock_logger.info.assert_called()

    @patch('reddit_mod.logger')
    def test_moderate_submission_remove(self, mock_logger):
        """Test removing a submission"""
        decision = {
            "violates": True,
            "rule_number": 1,
            "explanation": "This is spam"
        }
        
        result = reddit_mod.moderate_submission(self.submission, decision, self.rules)
        
        self.assertEqual(result, "Removed (Rule 1)")
        self.submission.mod.remove.assert_called_once()
        self.submission.mod.send_removal_message.assert_called_once()
        mock_logger.info.assert_called()

    @patch('reddit_mod.logger')
    def test_moderate_submission_dry_run(self, mock_logger):
        """Test dry run mode"""
        decision = {"violates": True, "rule_number": 1}
        
        result = reddit_mod.moderate_submission(
            self.submission, decision, self.rules, dry_run=True
        )
        
        self.assertEqual(result, "Removed (Rule 1)")
        # No actual Reddit API calls should be made
        self.submission.mod.remove.assert_not_called()
        self.submission.mod.send_removal_message.assert_not_called()
        mock_logger.info.assert_called()


if __name__ == "__main__":
    unittest.main()
