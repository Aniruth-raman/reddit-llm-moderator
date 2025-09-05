#!/usr/bin/env python3
"""
LLM Provider integration for Reddit LLM Moderator.

This module provides an extensible LLM interface for Reddit moderation.
Currently implements Google Gemini, but designed for easy extension to other providers.

Features:
- Abstract LLMProvider base class for extensibility
- GeminiLLMProvider implementation 
- Factory function supporting multiple providers
- Backward compatibility with legacy configurations

To add a new LLM provider:
1. Create a new class inheriting from LLMProvider
2. Implement the evaluate_text() method
3. Add provider detection to create_llm_provider()
4. Create a corresponding _create_<provider>_provider() function
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM provider implementations."""

    @abstractmethod
    def evaluate_text(self, prompt: str) -> Dict[str, Any]:
        """
        Evaluate text using the LLM provider.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Dict containing the evaluation result with keys:
            - violates: Boolean indicating if content violates rules
            - confidence: Float between 0-1 indicating confidence level
            - explanation: String explanation of the decision
            - rule_number: Integer rule number if violation found
            - error: String error message if evaluation failed
        """
        pass


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM provider for Reddit moderation tasks."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Google Gemini provider.

        Args:
            api_key: Google API key for authentication
            model: Model to use (default: gemini-1.5-pro)
        
        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")
        
        self.api_key = api_key.strip()
        self.model = model
        self._generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 0,
            "max_output_tokens": 500,
        }

    def evaluate_text(self, prompt: str) -> Dict[str, Any]:
        """
        Evaluate text using Google Gemini.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Dict containing the evaluation result with keys:
            - violates: Boolean indicating if content violates rules
            - confidence: Float between 0-1 indicating confidence level
            - explanation: String explanation of the decision
            - rule_number: Integer rule number if violation found
            - error: String error message if evaluation failed
        """
        if not prompt or not prompt.strip():
            return {"violates": False, "error": "Empty prompt provided"}

        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google-generativeai package not installed")
            return {"violates": False, "error": "Gemini package not available"}

        try:
            # Configure the Gemini API
            genai.configure(api_key=self.api_key)

            # Setup model
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=self._generation_config,
            )

            # Create comprehensive prompt
            system_prompt = (
                "You are a Reddit moderator assistant. "
                "Respond only with valid JSON containing your moderation decision."
            )
            full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate content
            response = model.generate_content(full_prompt)

            if not response or not response.text:
                return {"violates": False, "error": "Empty response from Gemini"}

            # Parse JSON response
            return self._parse_response(response.text)

        except Exception as e:
            error_msg = f"Google Gemini evaluation failed: {str(e)}"
            logger.error(error_msg)
            return {"violates": False, "error": error_msg}

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the response text to extract JSON.

        Args:
            response_text: Raw response text from Gemini

        Returns:
            Parsed JSON dictionary or error response
        """
        # First try direct JSON parsing
        try:
            result = json.loads(response_text)
            logger.debug(f"Successfully parsed JSON response: {result}")
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from wrapped text
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    logger.debug(f"Extracted JSON from wrapped text: {result}")
                    return result
                except json.JSONDecodeError:
                    pass

        # If all parsing fails
        error_msg = f"Could not parse JSON from response: {response_text[:100]}..."
        logger.error(error_msg)
        return {"violates": False, "error": error_msg}

    def __str__(self) -> str:
        """String representation of the provider."""
        masked_key = f"{'*' * (len(self.api_key) - 4)}{self.api_key[-4:]}" if len(self.api_key) >= 4 else "****"
        return f"GeminiLLMProvider(model={self.model}, api_key={masked_key})"


def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create an LLM provider from configuration.

    Args:
        config: Configuration dictionary containing provider settings.
                For Gemini: {'provider': 'gemini', 'api_key': '...', 'model': '...'}
                If no provider specified, defaults to Gemini for backward compatibility.

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If required configuration is missing or provider is unsupported
        
    Example:
        # Using explicit provider (recommended for new configs)
        config = {"provider": "gemini", "api_key": "key", "model": "gemini-1.5-pro"}
        provider = create_llm_provider(config)
        
        # Legacy format (backward compatibility)
        config = {"api_key": "key", "model": "gemini-1.5-pro"}  
        provider = create_llm_provider(config)
        
        # To add support for a new provider:
        # 1. Create a new class like OpenAILLMProvider(LLMProvider)
        # 2. Add it to the provider_type check below
        # 3. Create a _create_openai_provider() function
    """
    # Support both new format and legacy Gemini-only format
    if "provider" in config:
        provider_type = config["provider"].lower()
        if provider_type == "gemini":
            return _create_gemini_provider(config)
        # To add more providers, add elif conditions here:
        # elif provider_type == "openai":
        #     return _create_openai_provider(config)
        # elif provider_type == "anthropic":
        #     return _create_anthropic_provider(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")
    else:
        # Legacy format or direct Gemini config - assume Gemini
        return _create_gemini_provider(config)


def _create_gemini_provider(config: Dict[str, Any]) -> GeminiLLMProvider:
    """
    Internal function to create a Gemini provider from configuration.

    Args:
        config: Configuration dictionary with 'api_key' and optional 'model'

    Returns:
        Configured GeminiLLMProvider instance

    Raises:
        ValueError: If required configuration is missing
    """
    if "api_key" not in config:
        raise ValueError("Gemini configuration must include 'api_key'")

    return GeminiLLMProvider(
        api_key=config["api_key"],
        model=config.get("model", "gemini-1.5-pro")
    )


# Legacy function for backward compatibility
def create_gemini_provider(config: Dict[str, Any]) -> GeminiLLMProvider:
    """
    Legacy factory function for Gemini provider.
    
    Args:
        config: Configuration dictionary with 'api_key' and optional 'model'

    Returns:
        Configured GeminiLLMProvider instance

    Raises:
        ValueError: If required configuration is missing
    """
    return _create_gemini_provider(config)
