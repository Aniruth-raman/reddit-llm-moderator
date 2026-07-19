# Reddit LLM Moderator

Minimal CLI moderator for Reddit modqueue using OpenRouter.

## What it does

- Fetches unreported modqueue items (posts and comments) from one subreddit
- Skips items already reported by users, and items it has already reported itself
- Uses OpenRouter to evaluate each item against subreddit rules
- Takes two actions based on LLM confidence:
  - **approve**: high-confidence non-violations (above `approve_threshold`)
  - **report**: high-confidence violations (above `report_threshold`)
- Skips low-confidence items for manual review
- Stops the run early (instead of retrying item by item) if OpenRouter rate-limits or is unreachable — the next scheduled run picks up where it left off
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
  modqueue_limit: 16              # Max items to process per run
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
uv run main.py

# Dry-run: evaluate but don't approve/report
uv run main.py --dry-run

# Debug: verbose logging
uv run main.py --debug

# Combine options
uv run main.py --dry-run --debug
```

## Architecture

- **main.py**: CLI entrypoint, argument parsing, logging setup
- **openrouter.py**: OpenRouter API integration, prompt building, response parsing
- **moderation.py**: Moderation workflow, Reddit operations, config/rules loading

## Key Behaviors

- **Report filtering**: Items already reported by a user, or already reported by this bot (including reports a mod later dismissed), are skipped and never re-evaluated
- **Approval flow**: Non-violations with high confidence are auto-approved
- **Report flow**: Violations with high confidence are auto-reported with reason (character-limited to 99 chars)
- **Rate-limit handling**: A 429 or unreachable OpenRouter stops the rest of the run immediately rather than retrying every remaining item; the hourly schedule provides the backoff
- **Dry-run safety**: No actions taken, only logged
- **OpenRouter-only**: Single provider, hardcoded