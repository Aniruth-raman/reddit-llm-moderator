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

# Note: For demo purposes, we'll inline the create_llm_prompt function
# to avoid external dependencies
# from shared.utils import create_llm_prompt
from shared.Moderation import ModerationDecision
from shared.ModerationService import ModerationService


def create_llm_prompt(item, rules):
    """Create a prompt for the LLM to evaluate a Reddit item against rules."""
    rules_text = "\n".join(
        [
            f"Rule {rule['number']}: {rule['title']}\n"
            f"Explanation: {rule['explanation']}"
            for rule in rules
        ]
    )

    # Determine if the item is a submission or comment
    is_submission = hasattr(item, 'title')

    if is_submission:
        # Handle submission
        content_type = "submission"
        content_info = f"""SUBMISSION:
Title: {item.title}
Body: {item.selftext if hasattr(item, 'selftext') else '[No text content]'}
URL: {item.url if hasattr(item, 'url') else '[No URL]'}
Domain: {item.domain if hasattr(item, 'domain') else '[No domain]'}"""
    else:
        # Handle comment
        content_type = "comment"
        content_info = f"""COMMENT:
Body: {item.body}"""

    prompt = f"""
You are a Reddit moderator. Evaluate the following {content_type} against the subreddit's rules.
Respond with a JSON object containing your moderation decision.

SUBREDDIT RULES:
{rules_text}

{content_info}

If the {content_type} violates any rule, respond with:
{{
  "violates": true,
  "rule_number": [rule number],
  "explanation": "[your explanation why it violates this rule]",
  "confidence": [confidence score from 0.0 to 1.0]
}}

If the {content_type} does not violate any rule, respond with:
{{
  "violates": false,
  "confidence": [confidence score from 0.0 to 1.0]
}}

Always include a confidence score from 0.0 (not confident) to 1.0 (very confident) indicating how certain you are about your decision.
Respond ONLY with the JSON object, nothing else.
"""
    return prompt

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
        return {"violates": True, "rule_number": 1, "explanation": "Contains spam keywords", "confidence": 0.95}
    
    if any(word in combined_text for word in ["idiot", "stupid", "hate", "fool"]):
        return {"violates": True, "rule_number": 2, "explanation": "Contains uncivil language", "confidence": 0.9}
    
    if len(combined_text) < 20:
        return {"violates": True, "rule_number": 3, "explanation": "Low-quality/short content", "confidence": 0.7}
    
    if not any(word in combined_text for word in ["topic", "relevant", "discuss"]):
        return {"violates": True, "rule_number": 4, "explanation": "May be off-topic", "confidence": 0.6}
    
    # No violations found - confidence varies based on content quality
    if len(combined_text) > 100:
        confidence = 0.9  # High confidence for longer, detailed content
    elif len(combined_text) > 50:
        confidence = 0.8  # Medium-high confidence
    else:
        confidence = 0.6  # Lower confidence for shorter content
    
    return {"violates": False, "confidence": confidence}


def main():
    """Run example with mock data."""
    # Create mock rules for demo (avoiding YAML dependency)
    rules = [
        {
            "number": 1,
            "title": "No spam or self-promotion",
            "explanation": "Posts should not be primarily for self-promotion or spamming links.",
            "response": "Your submission has been removed for violating Rule 1: No spam or self-promotion."
        },
        {
            "number": 2, 
            "title": "Be civil and respectful",
            "explanation": "Treat others with respect. Personal attacks, hate speech, and harassment are not tolerated.",
            "response": "Your submission has been removed for violating Rule 2: Be civil and respectful."
        },
        {
            "number": 3,
            "title": "Quality content",
            "explanation": "Posts should be substantial and contribute to discussion.",
            "response": "Your submission has been removed for violating Rule 3: Quality content required."
        },
        {
            "number": 4,
            "title": "Stay on topic", 
            "explanation": "Posts should be relevant to the subreddit's purpose.",
            "response": "Your submission has been removed for violating Rule 4: Stay on topic."
        }
    ]
    
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
        create_mock_submission(
            "Maybe this could be about something",
            "Not sure if this belongs here or not."
        ),
    ]
    
    logger.info("DEMO MODE: Processing mock submissions with confidence thresholds")
    logger.info("=" * 70)
    logger.info("This demo shows how confidence scores affect moderation decisions")
    logger.info(f"Confidence threshold: 0.8 (only actions with confidence >= 0.8 will be taken)")
    logger.info("=" * 70)
    
    # Process each mock submission
    for submission in sample_submissions:
        logger.info(f"\n📋 Processing: '{submission.title}'")
        
        # Create the prompt that would be sent to the LLM
        prompt = create_llm_prompt(submission, rules)
        logger.info(f"🤖 LLM Prompt (abbreviated): {prompt[:100]}...")
        
        # Get mock evaluation with confidence score
        decision_data = mock_llm_evaluation(submission, rules)
        logger.info(f"📊 LLM Decision: {json.dumps(decision_data, indent=2)}")
        
        # Create decision object
        decision = ModerationDecision(decision_data)
        
        # Create mock subreddit for the demo
        mock_subreddit = MagicMock()
        
        # Use moderation service with confidence threshold
        moderation_service = ModerationService()
        confidence_threshold = 0.8  # Same as config default
        
        result = moderation_service.moderate_item(
            item=submission,
            decision=decision,
            rules=rules,
            subreddit=mock_subreddit,
            dry_run=True,
            confidence_threshold=confidence_threshold
        )
        
        # Enhanced result logging
        if result.action_taken == "approved":
            logger.info(f"✅ Result: APPROVED (confidence: {decision.confidence:.2f})")
        elif result.action_taken == "removed":
            logger.info(f"❌ Result: REMOVED - Rule {result.rule_number} (confidence: {decision.confidence:.2f})")
        elif result.action_taken == "no_action":
            logger.info(f"⏸️  Result: NO ACTION TAKEN (confidence: {decision.confidence:.2f})")
            
        if result.explanation:
            logger.info(f"📝 Explanation: {result.explanation}")
        logger.info("-" * 70)
    
    logger.info("\n🎉 Demo complete!")
    logger.info("\n📋 Key takeaways from this demo:")
    logger.info("• Confidence scores range from 0.0 (not confident) to 1.0 (very confident)")
    logger.info("• Only decisions with confidence >= threshold result in moderation actions")
    logger.info("• Low confidence decisions result in 'no action' - this prevents false positives")
    logger.info("• This makes the moderator more conservative and reliable")
    logger.info("• Threshold is configurable in config.yaml (llm.confidence_threshold)")

if __name__ == "__main__":
    main()
