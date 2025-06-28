#!/usr/bin/env python3
"""
Core LLM integration for Reddit LLM Moderator.
This module provides shared LLM functionality used by both CLI and MCP versions.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import requests

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
            Dict containing the evaluation result
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4-turbo)
        """
        self.api_key = api_key
        self.model = model

    def evaluate_text(self, prompt: str) -> Dict[str, Any]:
        """Evaluate text using OpenAI."""
        try:
            import openai

            self.client = openai.OpenAI(api_key=self.api_key)
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Reddit moderator assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.2,
            )

            raw_response = response.choices[0].message.content
            try:
                result = json.loads(raw_response)
                # Log the result for debugging
                logger.debug(f"Raw JSON response: {raw_response}")
                logger.debug(f"Parsed decision: {result}")

                # Ensure rule_number is properly formatted if present
                if (
                        "violates" in result
                        and result.get("violates")
                        and "rule_number" in result
                ):
                    rule_num = result["rule_number"]
                    # If rule_number is a string that can be converted to int, do so
                    if isinstance(rule_num, str) and rule_num.isdigit():
                        result["rule_number"] = int(rule_num)
                        logger.debug(
                            f"Converted rule_number from string '{rule_num}' to int {result['rule_number']}"
                        )

                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM: {e}")
                logger.error(f"Raw response: {raw_response}")
                return {"violates": False, "error": f"Invalid JSON response: {e}"}
        except Exception as e:
            logger.error(f"OpenAI evaluation failed: {e}")
            return {"violates": False, "error": str(e)}

    def __str__(self):
        return f"OpenAIProvider(model={self.model}, api_key={'*' * len(self.api_key[:-4]) + self.api_key[-4:]})"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation of LLM provider."""

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-opus-20240229)
        """
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"

    def evaluate_text(self, prompt: str) -> Dict[str, Any]:
        """Evaluate text using Anthropic Claude."""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }

            data = {
                "model": self.model,
                "max_tokens": 500,
                "temperature": 0.2,
                "system": "You are a Reddit moderator assistant. Respond only with valid JSON.",
                "messages": [{"role": "user", "content": prompt}],
            }

            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()

            response_data = response.json()
            content = response_data["content"][0]["text"]

            # Extract JSON from response
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Try to extract JSON from the content if it's wrapped in text
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    return result
                else:
                    raise ValueError("Could not parse JSON from response")

        except Exception as e:
            logger.error(f"Anthropic evaluation failed: {e}")
            return {"violates": False, "error": str(e)}

    def __str__(self):
        return f"AnthropicProvider(model={self.model}, api_key={'*' * len(self.api_key[:-4]) + self.api_key[-4:]})"


class GeminiProvider(LLMProvider):
    """Google Gemini implementation of LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Google Gemini provider.

        Args:
            api_key: Google API key
            model: Model to use (default: gemini-1.5-pro)
        """
        self.api_key = api_key
        self.model = model

    def evaluate_text(self, prompt: str) -> Dict[str, Any]:
        """Evaluate text using Google Gemini."""
        try:
            import google.generativeai as genai

            # Configure the Gemini API
            genai.configure(api_key=self.api_key)

            # Setup model
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 0,
                    "max_output_tokens": 500,
                },
            )

            # Create system prompt + user prompt
            system_prompt = (
                "You are a Reddit moderator assistant. Respond only with valid JSON."
            )
            full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate content
            response = model.generate_content(full_prompt)

            # Try parsing the response as JSON
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                # Try to extract JSON from the content if it's wrapped in text
                json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    return result
                else:
                    raise ValueError(
                        f"Could not parse JSON from response: {response.text[:100]}..."
                    )

        except Exception as e:
            logger.error(f"Google Gemini evaluation failed: {e}")
            return {"violates": False, "error": str(e)}

    def __str__(self):
        return f"GeminiProvider(model={self.model}, api_key={'*' * len(self.api_key[:-4]) + self.api_key[-4:]})"


class OllamaProvider(LLMProvider):
    """Ollama implementation of LLM provider for local LLM inference."""

    def __init__(self, model: str = "llama3", host: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.

        Args:
            model: Model name in Ollama (default: llama3)
            host: Ollama API host (default: http://localhost:11434)
        """
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"

    def evaluate_text(self, prompt: str) -> Dict[str, Any]:
        """Evaluate text using local Ollama instance."""
        try:
            headers = {"Content-Type": "application/json"}

            # Add clear instructions to return JSON
            system_prompt = (
                "You are a Reddit moderator assistant. Respond only with valid JSON."
            )
            full_prompt = f"{system_prompt}\n\n{prompt}\n\nRemember to respond ONLY with the JSON object, nothing else."

            data = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 500},
            }
            logger.info(
                f"Sending request to Ollama: {self.api_url} with headers= {headers} and json: {data}"
            )
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()

            response_data = response.json()
            content = response_data["response"]

            # Extract JSON from response
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Try to extract JSON from the content if it's wrapped in text
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    return result
                else:
                    raise ValueError(
                        f"Could not parse JSON from Ollama response: {content[:100]}..."
                    )

        except Exception as e:
            logger.error(f"Ollama evaluation failed: {e}")
            return {"violates": False, "error": str(e)}

    def __str__(self):
        return f"OllamaProvider(model={self.model}, host={self.host})"


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(
            provider_name: str, config: Dict[str, Any]
    ) -> Optional[LLMProvider]:
        """
        Create an LLM provider instance based on name and config.

        Args:
            provider_name: Name of the provider (openai, anthropic, gemini, ollama)
            config: Configuration dictionary with API keys and settings

        Returns:
            LLMProvider instance or None if provider is not supported
        """
        if provider_name == "openai":
            return OpenAIProvider(
                api_key=config["api_key"], model=config.get("model", "gpt-4-turbo")
            )
        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=config["api_key"],
                model=config.get("model", "claude-3-opus-20240229"),
            )
        elif provider_name == "gemini":
            return GeminiProvider(
                api_key=config["api_key"], model=config.get("model", "gemini-1.5-pro")
            )
        elif provider_name == "ollama":
            return OllamaProvider(
                model=config.get("model", "llama3"),
                host=config.get("host", "http://localhost:11434"),
            )
        else:
            logger.error(f"Unsupported LLM provider: {provider_name}")
            return None
