"""LLM evaluation with extensible provider support."""
import json
import google.generativeai as genai

def get_llm_evaluator(config):
    """Factory function to create LLM evaluator - extensible for other providers."""
    provider = config.get('llm_provider', {}).get('provider', 'gemini')
    
    if provider == 'gemini':
        return GeminiEvaluator(config['gemini'])
    # Add other providers here: elif provider == 'openai': ...
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

class GeminiEvaluator:
    def __init__(self, config):
        genai.configure(api_key=config['api_key'])
        self.model = genai.GenerativeModel(config.get('model', 'gemini-1.5-pro'))
    
    def evaluate(self, item, rules):
        """Evaluate Reddit item against rules using proper prompt engineering."""
        prompt = self._create_llm_prompt(item, rules)
        try:
            response = self.model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            return {"violates": False, "confidence": 0, "error": str(e)}
    
    def _create_llm_prompt(self, item, rules):
        """Create structured prompt for LLM evaluation."""
        rules_text = "\n".join([
            f"Rule {rule['number']}: {rule['title']}\nExplanation: {rule['explanation']}"
            for rule in rules
        ])
        
        # Determine content type and format
        is_submission = hasattr(item, 'title')
        if is_submission:
            content_info = f"""SUBMISSION:
Title: {item.title}
Body: {item.selftext if hasattr(item, 'selftext') else '[No text content]'}
URL: {item.url if hasattr(item, 'url') else '[No URL]'}"""
            content_type = "submission"
        else:
            content_info = f"""COMMENT:
Body: {item.body}
Author: {item.author.name if hasattr(item, 'author') and item.author else '[Deleted]'}"""
            content_type = "comment"
        
        return f"""You are a Reddit moderator. Evaluate the following {content_type} against the subreddit's rules.
Respond with a JSON object containing your moderation decision.

SUBREDDIT RULES:
{rules_text}

{content_info}

If the {content_type} violates any rule, respond with:
{{
  "violates": true,
  "rule_number": rule number,
  "explanation": "[your explanation why it violates this rule]",
  "confidence": [confidence score from 0.0 to 1.0]
}}

If the {content_type} does not violate any rule, respond with:
{{
  "violates": false,
  "confidence": [confidence score from 0.0 to 1.0]
}}"""

    def _parse_response(self, response_text):
        """Parse JSON response from LLM."""
        try:
            result = json.loads(response_text)
            # Convert confidence to 0-100 scale if needed
            if 'confidence' in result and result['confidence'] <= 1.0:
                result['confidence'] = int(result['confidence'] * 100)
            return result
        except json.JSONDecodeError:
            return {"violates": False, "confidence": 50, "error": "Invalid JSON response"}