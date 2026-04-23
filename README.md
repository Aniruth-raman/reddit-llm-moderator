# Reddit LLM Moderator

Minimal CLI moderator for Reddit modqueue using OpenRouter.

## What it does

- Fetches unreported modqueue items from one subreddit
- Filters out user-reported items (skips evaluating already flagged submissions)
- Uses OpenRouter to evaluate each item against subreddit rules
- Takes two actions based on LLM confidence:
  - **approve**: high-confidence non-violations (above `approve_threshold`)
  - **report**: high-confidence violations (above `report_threshold`)
- Skips low-confidence items for manual review
- Supports dry-run mode for safe testing

## Requirements

- Python 3.13+
- Reddit script app credentials (client ID, secret, username, password)
- OpenRouter API key

## Quick Start

```bash
uv sync
cp config.yaml.template config.yaml
cp rules.yaml.template rules.yaml
```

Edit `config.yaml` with your Reddit credentials and OpenRouter key, then edit `rules.yaml` with your subreddit rules.

## Configuration

```yaml
reddit:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  user_agent: "RedditModerator/1.0 by YourUsername"
  subreddit: "YourSubreddit"

moderation:
  modqueue_limit: 20              # Max items to process per run
  approve_threshold: 80           # % confidence to approve
  report_threshold: 70            # % confidence to report
  report_marker: "LLM-AUTO:"     # Prefix for report reason

llm_provider:
  api_key: "YOUR_OPENROUTER_API_KEY"
  model: "openai/gpt-4o-mini"
  base_url: "https://openrouter.ai/api/v1/chat/completions"
  site_url: "https://your-site.example.com"
  app_name: "reddit-llm-moderator"
```

## Usage

```bash
# Process modqueue with live actions
python main.py

# Dry-run: evaluate but don't approve/report
python main.py --dry-run

# Debug: verbose logging
python main.py --debug

# Combine options
python main.py --dry-run --debug
```

## Architecture

- **main.py**: CLI entrypoint, logging setup
- **models.py**: Domain types (Rule, ModerationItem, ModerationDecision)
- **openrouter.py**: OpenRouter API integration and evaluation logic
- **moderation.py**: Moderation workflow, Reddit operations, config loading

## Key Behaviors

- **User-report filtering**: Only unreported items are fetched and evaluated; user-reported submissions are skipped
- **Approval flow**: Non-violations with high confidence are auto-approved
- **Report flow**: Violations with high confidence are auto-reported with reason (character-limited to 99 chars)
- **Dry-run safety**: No actions taken, only logged
- **OpenRouter-only**: Single provider, hardcoded (no provider switching)

## Notes

- No moderation modes (no "enforce" vs "report_only"); always approve + report
- No remove action; only approve and report
- Report reasons are auto-truncated if they exceed Reddit's 100-char limit
