#!/usr/bin/env python3
"""
Example script to demonstrate how to use the Reddit Moderation CLI tool
with a mock API instead of real Reddit API calls.
"""

import sys
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from reddit_mod import load_rules, create_llm_prompt, moderate_submission

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_mock_submission(title, body, url="https://example.com"):
    """Create a mock submission object with the specified properties."""
    submission = MagicMock()
    submission.title = title
    submission.selftext = body
    submission.url = url
    submission.domain = url.split("//")[-1].split("/")[0]
    return submission


def mock_llm_evaluation(submission, rules):
    """Mock LLM evaluation for demonstration purposes."""
    # This is just a simple rule-based mock
    # In real usage, this would be replaced with a call to an LLM API
    
    combined_text = (submission.title + " " + submission.selftext).lower()
    
    # Example logic: check for rule violations
    if any(word in combined_text for word in ["spam", "buy now", "discount", "offer"]):
        return {"violates": True, "rule_number": 1, "explanation": "Contains spam keywords"}
    
    if any(word in combined_text for word in ["idiot", "stupid", "hate", "fool"]):
        return {"violates": True, "rule_number": 2, "explanation": "Contains uncivil language"}
    
    if len(combined_text) < 20:
        return {"violates": True, "rule_number": 3, "explanation": "Low-quality/short content"}
    
    if not any(word in combined_text for word in ["topic", "relevant", "discuss"]):
        return {"violates": True, "rule_number": 4, "explanation": "May be off-topic"}
    
    # No violations found
    return {"violates": False}


def main():
    """Run example with mock data."""
    # Load rules from the rules file
    rules = load_rules(Path(__file__).parent.parent / "rules.yaml")
    
    # Create sample mock submissions
    sample_submissions = [
        create_mock_submission(
            "Discussing the latest topic",
            "Here's a meaningful discussion about this relevant topic."
        ),
        create_mock_submission(
            "SPAM! Buy now at discount prices!!!",
            "Check out these amazing offers at our website!"
        ),
        create_mock_submission(
            "This community is stupid",
            "I hate how people here are so foolish."
        ),
        create_mock_submission(
            "hi",
            "just saying hi"
        ),
    ]
    
    logger.info("DEMO MODE: Processing mock submissions")
    logger.info("=" * 60)
    
    # Process each mock submission
    for submission in sample_submissions:
        logger.info(f"Processing: '{submission.title}'")
        
        # Create the prompt that would be sent to the LLM
        prompt = create_llm_prompt(submission, rules)
        logger.info(f"LLM Prompt (abbreviated): {prompt[:100]}...")
        
        # Get mock evaluation
        decision = mock_llm_evaluation(submission, rules)
        logger.info(f"LLM Decision: {json.dumps(decision)}")
        
        # Take moderation action (in dry-run mode)
        result = moderate_submission(submission, decision, rules, dry_run=True)
        logger.info(f"Result: {result}")
        logger.info("-" * 60)
    
    logger.info("Demo complete")


if __name__ == "__main__":
    main()
