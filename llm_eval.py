"""LLM evaluation with extensible provider support using SOLID principles."""
import json
import re
from abc import ABC, abstractmethod
import google.generativeai as genai


class LLMProvider(ABC):
    """Abstract base class for LLM providers following Interface Segregation Principle."""
    
    @abstractmethod
    def evaluate(self, item, rules):
        """Evaluate Reddit item against rules."""
        pass
    
    @abstractmethod
    def _generate_content(self, prompt):
        """Generate content from LLM provider."""
        pass


class LLMEvaluator:
    """Main evaluator class following Single Responsibility Principle."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    def evaluate(self, item, rules):
        """Delegate evaluation to the provider."""
        return self.provider.evaluate(item, rules)


class GeminiProvider(LLMProvider):
    """Gemini-specific implementation following Open/Closed Principle."""
    
    def __init__(self, config):
        genai.configure(api_key=config['api_key'])
        self.model = genai.GenerativeModel(config.get('model', 'gemini-1.5-pro'))
    
    def evaluate(self, item, rules):
        """Evaluate Reddit item against rules using proper prompt engineering."""
        prompt = self._create_llm_prompt(item, rules)
        try:
            response = self._generate_content(prompt)
            return self._parse_response(response)
        except Exception as e:
            return {"violates": False, "confidence": 0, "error": str(e)}
    
    def _generate_content(self, prompt):
        """Generate content using Gemini API."""
        response = self.model.generate_content(prompt)
        return response.text
    
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
            print(result)
            # Convert confidence to 0-100 scale if needed
            if "confidence" in result and result["confidence"] <= 1.0:
                result["confidence"] = int(result["confidence"] * 100)
            return result
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                raise ValueError(
                    f"Could not parse JSON from response: {response_text[:100]}..."
                )


class LLMProviderFactory:
    """Factory class following Factory Pattern for creating LLM providers."""
    
    @staticmethod
    def create_provider(config):
        """Create LLM provider based on configuration following Dependency Inversion Principle."""
        # Support both old and new config formats for backward compatibility
        if 'gemini' in config:
            # Legacy format
            provider_type = 'gemini'
            provider_config = config['gemini']
        elif 'llm_provider' in config:
            # New extensible format
            provider_type = config['llm_provider']['provider']
            provider_config = config['llm_provider']
        else:
            raise ValueError("No LLM provider configuration found")
        
        if provider_type == 'gemini':
            return GeminiProvider(provider_config)
        # Easy to extend: elif provider_type == 'openai': return OpenAIProvider(provider_config)
        # elif provider_type == 'anthropic': return AnthropicProvider(provider_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")


def get_llm_evaluator(config):
    """Factory function to create LLM evaluator with proper provider."""
    provider = LLMProviderFactory.create_provider(config)
    return LLMEvaluator(provider)