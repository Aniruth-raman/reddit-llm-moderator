import logging
from typing import Any

import praw
import yaml

from openrouter import ProviderError, evaluate

logger = logging.getLogger(__name__)
MAX_REDDIT_REPORT_REASON_LENGTH = 99


def load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as file_obj:
        config = yaml.safe_load(file_obj) or {}

    reddit = config.get("reddit", {})
    missing = [k for k in ("client_id", "client_secret", "username", "password", "subreddit") if not reddit.get(k)]
    if missing:
        raise ValueError(f"config.yaml: reddit section missing: {', '.join(missing)}")

    return config


def load_rules(rules_path: str) -> list[dict]:
    with open(rules_path, encoding="utf-8") as file_obj:
        payload = yaml.safe_load(file_obj) or {}
    rules = payload.get("rules")
    if not rules:
        raise ValueError("rules.yaml has no 'rules' list — refusing to run with zero rules")
    return rules


def create_reddit_client(config: dict):
    reddit = config["reddit"]
    return praw.Reddit(
        client_id=reddit["client_id"],
        client_secret=reddit["client_secret"],
        username=reddit["username"],
        password=reddit["password"],
        user_agent=reddit["user_agent"],
    )


def fetch_modqueue_items(reddit_client, subreddit_name: str, limit: int, report_marker: str):
    items: list[Any] = []
    for item in reddit_client.subreddit(subreddit_name).mod.modqueue(limit=None):
        if item.user_reports:
            continue
        reports = (getattr(item, "mod_reports", None) or []) + (getattr(item, "mod_reports_dismissed", None) or [])
        if any(reason.startswith(report_marker) for reason, _ in reports):
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def build_report_reason(decision: dict, report_marker: str) -> str:
    rule_number = decision.get("rule_number")
    rule_part = f"Rule {rule_number}" if rule_number is not None else "Rule"
    explanation = decision.get("explanation") or "Potential rule violation"
    full_reason = f"{report_marker} {rule_part}: {explanation}".strip()
    if len(full_reason) <= MAX_REDDIT_REPORT_REASON_LENGTH:
        return full_reason

    suffix = "..."
    limit = MAX_REDDIT_REPORT_REASON_LENGTH - len(suffix)
    return f"{full_reason[:limit].rstrip()}{suffix}"


def display_text(item: Any) -> str:
    is_submission = hasattr(item, "title")
    author = item.author.name if item.author else "[Deleted]"
    if is_submission:
        title = item.title if len(item.title) <= 63 else item.title[:60] + "..."
        return f'"{title}" by u/{author}'
    body = item.body if len(item.body) <= 83 else item.body[:80] + "..."
    return f'Comment: "{body}" by u/{author}'


def process_modqueue(
    reddit_client,
    provider_config: dict,
    subreddit_name: str,
    rules: list[dict],
    limit: int,
    settings: dict,
) -> None:
    items = fetch_modqueue_items(reddit_client, subreddit_name, limit, settings["report_marker"])
    logger.info("Fetched %s unreported items from r/%s", len(items), subreddit_name)
    logger.info("Settings: approve>=%s%%, report>=%s%%", settings["approve_threshold"], settings["report_threshold"])

    if not items:
        logger.info("No items in modqueue")
        return

    for index, raw_item in enumerate(items, 1):
        logger.info("[%s/%s] Processing item", index, len(items))
        try:
            process_item(raw_item, provider_config, rules, settings)
        except ProviderError:
            logger.error("Stopping run: LLM provider unavailable")
            break
        except Exception:
            logger.exception("Failed to process item id=%s", getattr(raw_item, "id", "unknown"))


def process_item(
    raw_item: Any,
    provider_config: dict,
    rules: list[dict],
    settings: dict,
) -> None:
    decision = evaluate(provider_config, raw_item, rules)
    confidence = decision["confidence"]
    permalink = f"https://reddit.com{raw_item.permalink}"

    if not decision["violates"] and confidence >= settings["approve_threshold"]:
        if settings["dry_run"]:
            logger.info("[DRY RUN] Would approve (confidence: %s%%)", confidence)
        else:
            raw_item.mod.approve()
            logger.info("APPROVE (confidence: %s%%)", confidence)
        logger.info("Content: %s", display_text(raw_item))
        if permalink:
            logger.info("Link: %s", permalink)
        return

    if decision["violates"] and confidence >= settings["report_threshold"]:
        reason = build_report_reason(decision, settings["report_marker"])
        if settings["dry_run"]:
            logger.info("[DRY RUN] Would report (confidence: %s%%)", confidence)
        else:
            raw_item.report(reason=reason)
            logger.info("REPORT (confidence: %s%%)", confidence)
        logger.info("Content: %s", display_text(raw_item))
        logger.info("Reason: %s", reason)
        if permalink:
            logger.info("Link: %s", permalink)
        return

    logger.info("Skipped (confidence: %s%%): %s", confidence, display_text(raw_item))
    if permalink:
        logger.debug("Link: %s", permalink)
