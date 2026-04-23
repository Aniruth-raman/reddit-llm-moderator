import logging
from typing import Any

import praw
import yaml

import openrouter
from models import ModerationDecision, ModerationItem, Rule

logger = logging.getLogger(__name__)
MAX_REDDIT_REPORT_REASON_LENGTH = 99


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as file_obj:
        config = yaml.safe_load(file_obj) or {}

    if not isinstance(config, dict):
        raise ValueError("Config must be a YAML object")

    reddit = config.get("reddit")
    moderation = config.get("moderation")
    llm_provider = config.get("llm_provider")

    if not isinstance(reddit, dict):
        raise ValueError("Missing required section: reddit")
    if not isinstance(moderation, dict):
        raise ValueError("Missing required section: moderation")
    if not isinstance(llm_provider, dict):
        raise ValueError("Missing required section: llm_provider")

    for key in ["client_id", "client_secret", "username", "password", "user_agent", "subreddit"]:
        if not reddit.get(key):
            raise ValueError(f"Missing reddit config key: {key}")

    for key in ["modqueue_limit", "approve_threshold", "report_threshold"]:
        if key not in moderation:
            raise ValueError(f"Missing moderation config key: {key}")

    if not llm_provider.get("api_key"):
        raise ValueError("Missing llm_provider.api_key")

    return config


def load_rules(rules_path: str) -> list[Rule]:
    with open(rules_path, "r", encoding="utf-8") as file_obj:
        payload = yaml.safe_load(file_obj) or {}

    rules_data = payload.get("rules")
    if not isinstance(rules_data, list):
        raise ValueError("'rules' must be a list in rules.yaml")

    rules: list[Rule] = []
    for index, rule in enumerate(rules_data, 1):
        if not isinstance(rule, dict):
            raise ValueError(f"Rule at index {index} must be an object")
        rules.append(
            Rule(
                number=int(rule.get("number", index)),
                title=str(rule.get("title", "Untitled rule")),
                explanation=str(rule.get("explanation", "")),
            )
        )

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


def fetch_modqueue_items(reddit_client, subreddit_name: str, limit: int):
    items: list[Any] = []
    for item in reddit_client.subreddit(subreddit_name).mod.modqueue(limit=None):
        if has_user_report(item):
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def approve_item(item) -> None:
    item.mod.approve()


def report_item(item, reason: str) -> None:
    item.report(reason=reason)


def has_bot_report(item, marker: str) -> bool:
    mod_reports = getattr(item, "mod_reports", None) or []
    for report in mod_reports:
        reason = report[0] if isinstance(report, (tuple, list)) and report else report
        if isinstance(reason, str) and marker in reason:
            return True
    return False


def has_user_report(item) -> bool:
    user_reports = getattr(item, "user_reports", None) or []
    for report in user_reports:
        if isinstance(report, (tuple, list)) and len(report) >= 2:
            try:
                if int(report[1]) > 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def build_report_reason(decision: ModerationDecision, report_marker: str) -> str:
    rule_part = f"Rule {decision.rule_number}" if decision.rule_number is not None else "Rule"
    explanation = decision.explanation or "Potential rule violation"
    full_reason = f"{report_marker} {rule_part}: {explanation}".strip()
    if len(full_reason) <= MAX_REDDIT_REPORT_REASON_LENGTH:
        return full_reason

    suffix = "..."
    limit = MAX_REDDIT_REPORT_REASON_LENGTH - len(suffix)
    return f"{full_reason[:limit].rstrip()}{suffix}"


def to_moderation_item(item: Any) -> ModerationItem:
    author = item.author.name if hasattr(item, "author") and item.author else "[Deleted]"
    if hasattr(item, "title"):
        return ModerationItem(
            item_id=getattr(item, "id", "unknown"),
            item_type="submission",
            title=getattr(item, "title", "[No title]"),
            body=getattr(item, "selftext", "") or "",
            author=author,
            permalink=f"https://reddit.com{item.permalink}" if hasattr(item, "permalink") else "",
        )
    return ModerationItem(
        item_id=getattr(item, "id", "unknown"),
        item_type="comment",
        title="",
        body=getattr(item, "body", "[No body]"),
        author=author,
        permalink=f"https://reddit.com{item.permalink}" if hasattr(item, "permalink") else "",
    )


def display_text(item: ModerationItem) -> str:
    if item.item_type == "submission":
        title = item.title[:60] + "..." if len(item.title) > 60 else item.title
        return f'"{title}" by u/{item.author}'
    body = (item.body[:80] + "..." if len(item.body) > 80 else item.body).replace("\n", " ").replace("\r", " ")
    return f'Comment: "{body}" by u/{item.author}'


def process_modqueue(
    reddit_client,
    provider_config: dict,
    subreddit_name: str,
    rules: list[Rule],
    limit: int,
    approve_threshold: int,
    report_threshold: int,
    dry_run: bool,
    report_marker: str,
) -> None:
    items = fetch_modqueue_items(reddit_client, subreddit_name, limit)
    logger.info("Fetched %s unreported items from r/%s", len(items), subreddit_name)
    logger.info("Settings: approve>=%s%%, report>=%s%%", approve_threshold, report_threshold)

    if not items:
        logger.info("No items in modqueue")
        return

    for index, raw_item in enumerate(items, 1):
        logger.info("[%s/%s] Processing item", index, len(items))
        try:
            process_item(
                raw_item,
                provider_config,
                rules,
                approve_threshold,
                report_threshold,
                dry_run,
                report_marker,
            )
        except Exception:
            logger.exception("Failed to process item id=%s", getattr(raw_item, "id", "unknown"))


def process_item(
    raw_item: Any,
    provider_config: dict,
    rules: list[Rule],
    approve_threshold: int,
    report_threshold: int,
    dry_run: bool,
    report_marker: str,
) -> None:
    item = to_moderation_item(raw_item)

    if item.item_type == "submission" and has_bot_report(raw_item, report_marker):
        logger.info("Skipped (already reported by bot): %s", display_text(item))
        if item.permalink:
            logger.debug("Link: %s", item.permalink)
        return

    decision = openrouter.evaluate(provider_config, item, rules)
    if not decision.violates and decision.confidence >= approve_threshold:
        if dry_run:
            logger.info("[DRY RUN] Would approve (confidence: %s%%)", decision.confidence)
        else:
            approve_item(raw_item)
            logger.info("APPROVE (confidence: %s%%)", decision.confidence)
        logger.info("Content: %s", display_text(item))
        if item.permalink:
            logger.info("Link: %s", item.permalink)
        return

    if decision.violates and decision.confidence >= report_threshold:
        reason = build_report_reason(decision, report_marker)
        if dry_run:
            logger.info("[DRY RUN] Would report (confidence: %s%%)", decision.confidence)
        else:
            report_item(raw_item, reason)
            logger.info("REPORT (confidence: %s%%)", decision.confidence)
        logger.info("Content: %s", display_text(item))
        logger.info("Reason: %s", reason)
        if item.permalink:
            logger.info("Link: %s", item.permalink)
        return

    logger.info("Skipped (confidence: %s%%): %s", decision.confidence, display_text(item))
    if item.permalink:
        logger.debug("Link: %s", item.permalink)
