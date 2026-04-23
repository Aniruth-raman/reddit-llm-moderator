# Running Reddit LLM Moderator

Instructions for setting up and running the Reddit LLM Moderator.

## Prerequisites

- Python 3.13+
- Reddit API credentials:
  - Client ID
  - Client secret
  - Reddit username
  - Reddit password
- OpenRouter API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Aniruth-raman/reddit-llm-moderator.git
   cd reddit-llm-moderator
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create config and rules:
   ```bash
   cp config.yaml.template config.yaml
   cp rules.yaml.template rules.yaml
   ```

4. Edit files with your values.

## Configuration

### Reddit credentials

```yaml
reddit:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  user_agent: "RedditModerator/1.0 by YourUsername"
  subreddit: "YourSubreddit"
```

### Moderation settings

```yaml
moderation:
  modqueue_limit: 20              # Max items to process per run
  approve_threshold: 80           # Confidence % to auto-approve
  report_threshold: 70            # Confidence % to auto-report
  report_marker: "LLM-AUTO:"     # Prefix for report reason
```

**Workflow**:
- Fetches unreported modqueue items (stops when limit reached)
- User-reported items are skipped (not evaluated by LLM)
- Each item evaluated against rules by OpenRouter
- If confidence > `approve_threshold`: approved
- If confidence > `report_threshold`: reported with prefixed reason
- Otherwise: skipped for manual review

### OpenRouter (hardcoded provider)

```yaml
llm_provider:
  api_key: "YOUR_OPENROUTER_API_KEY"
  model: "openai/gpt-4o-mini"    # Any OpenRouter model
  base_url: "https://openrouter.ai/api/v1/chat/completions"
  site_url: "https://your-site.example.com"
  app_name: "reddit-llm-moderator"
```

## CLI Usage

```bash
# Process modqueue
python main.py

# Dry-run (no actions taken)
python main.py --dry-run

# Debug logging
python main.py --debug

# Combined
python main.py --dry-run --debug

# Custom paths
python main.py --config my_config.yaml --rules my_rules.yaml
python main.py --log-file moderation.log
```

## Behavior

### What happens in each run

1. Load config and rules
2. Authenticate with Reddit
3. Fetch unreported modqueue items (up to `modqueue_limit`)
4. For each item:
   - Evaluate against rules with OpenRouter
   - Approve if confidence > `approve_threshold`
   - Report if confidence > `report_threshold`
   - Skip if low confidence
5. In dry-run: log actions without executing
6. In normal mode: execute approve/report actions

### User-report filtering

- Items already reported by users are skipped entirely
- Only unreported items are sent to LLM for evaluation
- This avoids redundant processing and trust modqueue user feedback

### Report reason handling

- Report reason is prefixed with `report_marker` (e.g., "LLM-AUTO:")
- Reason is auto-truncated if final string exceeds 99 characters
- Reddit enforces a 100-character limit; truncation ensures compliance

## Troubleshooting

### Debug logging

```bash
python main.py --debug
```

### Validation checklist

- [ ] YAML format valid in `config.yaml` and `rules.yaml`
- [ ] Reddit credentials correct (test via `reddit.user.me()`)
- [ ] OpenRouter API key valid and has quota
- [ ] Subreddit name correct in config
- [ ] Rules file has at least one rule
- [ ] Start with `--dry-run` before production

### Common issues

- **Authentication fails**: Check Reddit credentials and user agent
- **API errors**: Verify OpenRouter API key has remaining quota
- **YAML parsing error**: Validate file syntax (use `yamllint` or online validator)
- **Empty modqueue**: Normal if subreddit has low traffic; try `--dry-run` to confirm connection
