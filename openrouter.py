import json
import logging
import re
from typing import Any
from urllib import error, request

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base for LLM provider failures that should halt the run."""


def evaluate(provider_config: dict, item: Any, rules: list[dict]) -> dict:
    prompt = create_prompt(item, rules)
    return parse_response(generate_content(provider_config, prompt))


def create_prompt(item: Any, rules: list[dict]) -> str:
    rules_text = "\n".join(f"{rule.get('number', idx)}. {rule.get('title', 'Untitled')}: {rule.get('explanation', '')}" for idx, rule in enumerate(rules, 1))
    is_submission = hasattr(item, "title")
    author = item.author.name if item.author else "[Deleted]"
    permalink = f"https://reddit.com{item.permalink}"

    if is_submission:
        content_info = f"SUBMISSION:\nTitle: {item.title}\nBody: {item.selftext or '[No text content]'}\nAuthor: {author}\nPermalink: {permalink}"
        content_type = "submission"
    else:
        content_info = f"COMMENT:\nBody: {item.body}\nAuthor: {author}\nPermalink: {permalink}"
        content_type = "comment"

    return f"""You are a Reddit moderator.
    Evaluate the following {content_type} against the rules below.
    Respond only with valid JSON.

    Rules:
    {rules_text}

    Content:
    {content_info}

    Return one of these JSON formats:

    If violates:
    {{
      \"violates\": true,
      \"rule_number\": <integer>,
      \"explanation\": \"<why it violates>\",
      \"confidence\": <integer from 0 to 100>
    }}

    If does not violate:
    {{
      \"violates\": false,
      \"confidence\": <integer from 0 to 100>
    }}"""


def parse_response(response_text: str) -> dict:
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not match:
            logger.error("Could not parse JSON from response: %s", response_text[:120])
            raise ValueError("Could not parse JSON from model response")
        result = json.loads(match.group(0))

    confidence = normalize_confidence(result.get("confidence", 0))
    rule_number = result.get("rule_number")
    return {
        "violates": bool(result.get("violates", False)),
        "confidence": confidence,
        "rule_number": int(rule_number) if rule_number is not None else None,
        "explanation": str(result.get("explanation", "")).strip(),
    }


def normalize_confidence(value) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, int(round(numeric))))


def generate_content(provider_config: dict, prompt: str) -> str:
    model = provider_config.get("model", "openai/gpt-4o-mini")
    base_url = provider_config.get("base_url", "https://openrouter.ai/api/v1/chat/completions")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    body = json.dumps(payload).encode("utf-8")

    headers = {"Authorization": f"Bearer {provider_config['api_key']}", "Content-Type": "application/json"}
    if provider_config.get("site_url"):
        headers["HTTP-Referer"] = provider_config["site_url"]
    if provider_config.get("app_name"):
        headers["X-Title"] = provider_config["app_name"]

    req = request.Request(base_url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=45) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        if exc.code == 429:
            raise ProviderError("Openrouter rate limited") from exc
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "OpenRouter request failed with HTTP %s for model %s at %s: %s",
            exc.code,
            model,
            base_url,
            error_body[:500],
        )
        raise
    except error.URLError as exc:
        logger.error("OpenRouter unreachable at %s: %s", base_url, exc.reason)
        raise ProviderError(f"OpenRouter unreachable: {exc.reason}") from exc

    choices = response_payload.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter response did not contain choices")
    return choices[0].get("message", {}).get("content", "")
