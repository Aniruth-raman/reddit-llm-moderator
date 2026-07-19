# GitHub Workflow Setup

Set up the Reddit LLM Moderator to run on GitHub Actions.

## Overview

The workflow provides:
- **On-demand execution**: Manual trigger via GitHub Actions UI
- **Secret-based configuration**: Credentials passed via GitHub secrets (safe, no repo exposure)
- **Flexible modes**: Dry-run and debug options
- **Fast execution**: ~1-2 minutes (depends on modqueue size)
- **Timeout protection**: 10-minute max to prevent runaway

## Required Secrets

Add these to your GitHub repository under **Settings → Secrets and variables → Actions**:

### 1. CONFIG

Your complete configuration as a YAML string:

```yaml
reddit:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  user_agent: "RedditModerator/1.0 by YourUsername"
  subreddit: "YourSubreddit"

moderation:
  modqueue_limit: 16
  approve_threshold: 80
  report_threshold: 70
  report_marker: "LLM-AUTO:"

llm_provider:
  api_key: "YOUR_OPENROUTER_API_KEY"
  model: "openai/gpt-4o-mini"
  base_url: "https://openrouter.ai/api/v1/chat/completions"
  site_url: "https://your-site.example.com"
  app_name: "reddit-llm-moderator"
```

### 2. RULES

Your subreddit rules as a YAML string:

```yaml
rules:
  - number: 1
    title: "No spam or self-promotion"
    explanation: "Posts should not be primarily for self-promotion or spamming links."
  
  - number: 2
    title: "Be civil and respectful"
    explanation: "Treat others with respect. Personal attacks, hate speech, and harassment are not tolerated."
  
  - number: 3
    title: "Stay on topic"
    explanation: "Posts should be relevant to the subreddit's purpose."
```

## Setting Up Secrets

1. Go to your GitHub repository
2. Click **Settings**
3. Left sidebar: **Secrets and variables → Actions**
4. Click **New repository secret**
5. Add secret `CONFIG` with your config YAML
6. Add secret `RULES` with your rules YAML

## Running the Workflow

1. Go to **Actions** tab
2. Select the **Moderate** workflow
3. Click **Run workflow**
4. Set options:
   - `dry_run`: `true` = evaluate only, no actions
   - `debug`: `true` = verbose logs
5. Click **Run workflow**

## Modes

### Safe Testing

```
dry_run: true
debug: true
```

Evaluates modqueue, logs decisions, but doesn't approve/report. Good for validation.

### Production

```
dry_run: false
debug: false
```

Evaluates modqueue and takes moderation actions (approve/report) based on confidence thresholds.

## Workflow Behavior

1. Load config and rules from secrets
2. Authenticate with Reddit
3. Fetch unreported, not-yet-bot-reported modqueue items (posts and comments)
4. Evaluate each with OpenRouter
5. Approve/report based on thresholds; stop early if OpenRouter rate-limits or is unreachable
6. Log results

### Report filtering

Items already reported by a user are skipped (never auto-actioned). Items this bot has already reported are also skipped, so they aren't re-evaluated or re-reported on later runs. Only items with neither kind of report go to the LLM.

## Security

- Secrets never exposed in logs
- Credentials only available during workflow execution
- All sensitive data stored in GitHub Secrets (not in repo)
- 10-minute timeout prevents runaway execution

## Local Testing Before Production

```bash
# Copy secrets to config files
cp config.yaml.template config.yaml
cp rules.yaml.template rules.yaml
# Edit with your values...

# Test in dry-run
uv run main.py --dry-run --debug

# Test normal execution
uv run main.py --debug
```

## Troubleshooting

### Workflow fails to run

- Verify both `CONFIG` and `RULES` secrets exist in GitHub
- Check YAML syntax (use `yamllint` or online validator)
- Confirm secret values are complete (not truncated in GitHub UI)

### Workflow runs but no actions taken

- Check confidence thresholds (maybe all items below thresholds)
- Look at workflow logs for evaluation scores
- Try with higher thresholds first, then lower to find sweet spot

### Workflow times out

- Reduce `modqueue_limit` in config
- Check OpenRouter API latency
- Run with smaller batch first

### Reddit authentication fails

- Verify Reddit credentials (test locally first)
- Confirm username is account name, not display name
- Check user agent format