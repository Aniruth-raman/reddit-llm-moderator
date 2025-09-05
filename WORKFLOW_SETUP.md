# GitHub Workflow Setup

This document explains how to set up and use the minimal GitHub workflow for Reddit moderation.

## Required GitHub Secrets

You need to set up the following secrets in your GitHub repository:

### 1. REDDIT_CONFIG_YAML

This should contain your complete configuration as a YAML string:

```yaml
reddit:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET" 
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  user_agent: "RedditModerator/1.0 by YourUsername"
  subreddit: "YourSubreddit"

approve_threshold: 80
remove_threshold: 70

llm_provider:
  provider: "gemini"
  api_key: "YOUR_GEMINI_API_KEY"
  model: "gemini-1.5-pro"
```

### 2. REDDIT_RULES_YAML

This should contain your subreddit rules as a YAML string:

```yaml
rules:
  - number: 1
    title: "No spam or self-promotion"
    explanation: "Posts should not be primarily for self-promotion or spamming links."
    response: "Your submission has been removed for violating Rule 1: No spam or self-promotion."
    notification_method: "public"
  
  - number: 2
    title: "Be civil and respectful"
    explanation: "Treat others with respect. Personal attacks, hate speech, and harassment are not tolerated."
    response: "Your submission has been removed for violating Rule 2: Be civil and respectful."
    notification_method: "modmail"
```

## Setting Up Secrets

1. Go to your GitHub repository
2. Click on "Settings" tab
3. In the left sidebar, click on "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Add both `REDDIT_CONFIG_YAML` and `REDDIT_RULES_YAML` secrets

## Running the Workflow

1. Go to the "Actions" tab in your repository
2. Select "Reddit Moderation Pipeline" workflow
3. Click "Run workflow"
4. Configure the options:
   - **dry_run**: Set to `true` to see what would happen without taking action
   - **disable_remove**: Set to `true` to comment out line 139 (disable remove actions)
   - **debug**: Set to `true` for detailed logging

## Workflow Features

- **Minimal footprint**: Uses only necessary dependencies
- **10-minute timeout**: Ensures quick execution
- **Manual trigger only**: Runs only when you need it
- **Secret-based configuration**: No sensitive data in repository
- **Flexible options**: Control dry-run, remove actions, and logging

## Security Notes

- All sensitive configuration is stored in GitHub Secrets
- The workflow never exposes secret values in logs
- Secrets are only available during workflow execution
- The workflow has a timeout to prevent runaway processes