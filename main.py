#!/usr/bin/env python3
import argparse
import logging
import sys

from moderation import create_reddit_client, load_config, load_rules, process_modqueue

logger = logging.getLogger(__name__)


def configure_logging(debug: bool, log_file: str | None) -> None:
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(console)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        root.addHandler(file_handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reddit LLM Moderator")
    parser.add_argument("--dry-run", action="store_true", help="Run without taking moderation actions")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", type=str, help="Log to specified file")
    parser.add_argument("--config", type=str, default="config.yaml", help="Configuration file path")
    parser.add_argument("--rules", type=str, default="rules.yaml", help="Rules file path")
    args = parser.parse_args()

    configure_logging(args.debug, args.log_file)

    try:
        config = load_config(args.config)
        rules = load_rules(args.rules)
        reddit_client = create_reddit_client(config)
        moderation = config["moderation"]
        process_modqueue(
            reddit_client=reddit_client,
            provider_config=config["llm_provider"],
            subreddit_name=config["reddit"]["subreddit"],
            rules=rules,
            limit=int(moderation["modqueue_limit"]),
            approve_threshold=int(moderation["approve_threshold"]),
            report_threshold=int(moderation["report_threshold"]),
            dry_run=args.dry_run,
            report_marker=str(moderation.get("report_marker", "LLM-AUTO:")),
        )
    except Exception:
        logger.exception("Moderation run failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
