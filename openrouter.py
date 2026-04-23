import json
import logging
import re
from urllib import error, request

from models import ModerationDecision, ModerationItem, Rule

logger = logging.getLogger(__name__)


def evaluate(provider_config: dict, item: ModerationItem, rules: list[Rule]) -> ModerationDecision:
    prompt = create_prompt(item, rules)
    return parse_response(generate_content(provider_config, prompt))


def create_prompt(item: ModerationItem, rules: list[Rule]) -> str:
    rules_text = "\n".join(f"{rule.number}. {rule.title}: {rule.explanation}" for rule in rules)
    if item.item_type == "submission":
        content_info = (
            f"SUBMISSION:\n"
            f"Title: {item.title}\n"
            f"Body: {item.body or '[No text content]'}\n"
            f"Author: {item.author}\n"
            f"Permalink: {item.permalink or '[No URL]'}"
        )
        content_type = "submission"
    else:
        content_info = (
            f"COMMENT:\n"
            f"Body: {item.body}\n"
            f"Author: {item.author}\n"
            f"Permalink: {item.permalink or '[No URL]'}"
        )
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
  \"confidence\": <number from 0 to 1 or 0 to 100>
}}

If does not violate:
{{
  \"violates\": false,
  \"confidence\": <number from 0 to 1 or 0 to 100>
}}"""


def parse_response(response_text: str) -> ModerationDecision:
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
    return ModerationDecision(
        violates=bool(result.get("violates", False)),
        confidence=confidence,
        rule_number=int(rule_number) if rule_number is not None else None,
        explanation=str(result.get("explanation", "")).strip(),
    )


def normalize_confidence(value) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if numeric <= 1.0:
        numeric *= 100
    return max(0, min(100, int(round(numeric))))


def generate_content(provider_config: dict, prompt: str) -> str:
    payload = {
        "model": provider_config.get("model", "openai/gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    body = json.dumps(payload).encode("utf-8")

    headers = {"Authorization": f"Bearer {provider_config['api_key']}", "Content-Type": "application/json"}
    if provider_config.get("site_url"):
        headers["HTTP-Referer"] = provider_config["site_url"]
    if provider_config.get("app_name"):
        headers["X-Title"] = provider_config["app_name"]

    req = request.Request(
        provider_config.get("base_url", "https://openrouter.ai/api/v1/chat/completions"),
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "OpenRouter request failed with HTTP %s for model %s at %s: %s",
            exc.code,
            provider_config.get("model", "openai/gpt-4o-mini"),
            provider_config.get("base_url", "https://openrouter.ai/api/v1/chat/completions"),
            error_body[:500],
        )
        raise

    choices = response_payload.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter response did not contain choices")
    return choices[0].get("message", {}).get("content", "")
