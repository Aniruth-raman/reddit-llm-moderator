# Reddit LLM Moderator

A Python tool that leverages AI language models to help moderate Reddit content based on subreddit rules. This project
supports both a command-line interface (CLI) and an API server following the Model Context Protocol (MCP) design
pattern.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

- Authentication with Reddit using script credentials
- Loading subreddit rules from a YAML file
- Fetching modqueue items from a specified subreddit
- Support for moderating both submissions and comments
- LLM analysis of content against subreddit rules
- Support for multiple LLM providers:
    - OpenAI (GPT-4, etc.)
    - Anthropic (Claude)
    - Google Gemini
    - Ollama (local deployment)
- Flexible notification options:
    - Public comments for transparency
    - Private modmail for sensitive issues
- **Confidence-based moderation**: Only take action when AI confidence meets threshold
- Automatic moderation actions (approve/remove) based on LLM decisions
- Item type filtering (submissions, comments, or both)
- Robust rule matching with type-conversion fallbacks
- Debug mode for troubleshooting
- Optional dry run mode to simulate actions without taking them
- Available as both CLI tool and MCP server

## Repository Structure

```
reddit-llm-moderator/
├── main.py                    # Main entry point for both CLI and MCP modes
├── requirements.txt           # Project dependencies
├── config.yaml.template      # Template for configuration file
├── rules.yaml.template       # Template for rules configuration
├── cli/                      # Command-line interface implementation
│   └── moderator.py         # CLI-specific moderation logic
├── mcp/                      # Model Context Protocol server implementation
│   └── server.py            # MCP server implementation with FastAPI
├── shared/                   # Shared code used by both CLI and MCP
│   ├── LLMProvider.py       # LLM provider implementations (OpenAI, Anthropic, Gemini, Ollama)
│   ├── Moderation.py        # Core moderation data models
│   ├── ModerationService.py # Moderation service implementation
│   ├── NotificationStrategy.py # Notification strategies (public/modmail)
│   ├── RuleMatcher.py       # Rule matching logic with type conversion
│   └── utils.py             # Utility functions and logging
├── examples/                 # Example implementations and demos
│   ├── demo.py              # Demo script
│   └── mcp_client.py        # MCP client example
└── tests/                    # Test suite
    └── test_reddit_mod.py   # Unit tests
```

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy the template files and configure them:
   ```
   cp config.yaml.template config.yaml
   cp rules.yaml.template rules.yaml
   ```
4. Edit `config.yaml` with your Reddit API credentials and API keys for your chosen LLM provider(s)
5. Edit `rules.yaml` with your subreddit rules
6. Make sure you have moderator permissions on the target subreddit

### Reddit API Setup

1. Create a Reddit App at https://www.reddit.com/prefs/apps/
2. Select "script" as the application type
3. Note your client ID and client secret
4. Use your Reddit username and password for authentication
5. Use a descriptive user agent to identify your bot

## Usage

### CLI Mode

Basic usage:

```
python main.py --mode=cli --subreddit=SUBREDDIT_NAME [--dry-run]
```

All available options:

```
python main.py --mode=cli --subreddit=SUBREDDIT_NAME [--dry-run] [--type=all|submissions|comments] [--notification=public|modmail] [--config=config.yaml] [--rules=rules.yaml] [--debug]
```

Examples:

```
# Process only comments, sending removal reasons via modmail
python main.py --mode=cli --subreddit=MySubreddit --type=comments --notification=modmail

# Simulate moderation of submissions only with debug output
python main.py --mode=cli --subreddit=MySubreddit --type=submissions --dry-run --debug

# Use specific config and rules files
python main.py --mode=cli --subreddit=MySubreddit --config=my_config.yaml --rules=my_rules.yaml
```

### MCP Server Mode

Start the server:

```
python main.py --mode=mcp
```

The server will start on port 8000 by default and provide the following endpoints:

- `POST /initialize`: Initialize the server with config and rules
- `GET /modqueue`: Get items from the modqueue
- `POST /moderate`: Moderate a specific item
- `GET /rules`: Get the configured rules

## Configuration Files

### config.yaml

Example configuration (copy from `config.yaml.template` and fill in your values):

```yaml
reddit:
  client_id: YOUR_CLIENT_ID
  client_secret: YOUR_CLIENT_SECRET
  username: YOUR_REDDIT_USERNAME
  password: YOUR_REDDIT_PASSWORD
  user_agent: "python:reddit-mod-bot:v1.0 (by /u/YOUR_USERNAME)"

# LLM Configuration
llm:
  provider: "openai"  # Options: "openai", "anthropic", "gemini", "ollama"
  confidence_threshold: 0.8  # Minimum confidence (0.0-1.0) required to take action

# OpenAI Configuration
openai:
  api_key: YOUR_OPENAI_API_KEY
  model: "gpt-4-turbo"  # Optional

# Anthropic Configuration
anthropic:
  api_key: YOUR_ANTHROPIC_API_KEY
  model: "claude-3-opus-20240229"  # Optional

# Google Gemini Configuration
gemini:
  api_key: YOUR_GEMINI_API_KEY
  model: "gemini-1.5-pro"  # Optional

# Ollama Configuration (local LLM)
ollama:
  model: "llama3"  # Required, specify the model you've pulled to Ollama
  host: "http://localhost:11434"  # Optional, defaults to http://localhost:11434
```

### rules.yaml

Example rules configuration (copy from `rules.yaml.template` and customize):

```yaml
rules:
  - number: 1
    title: "No spam or self-promotion"
    explanation: "Posts should not be primarily for self-promotion or spamming links."
    response: "Your submission has been removed for violating Rule 1: No spam or self-promotion."
    notification_method: "public"  # Optional: "public" (default) or "modmail"

  - number: 2
    title: "Be civil and respectful"
    explanation: "Treat others with respect. Personal attacks, hate speech, and harassment are not tolerated."
    response: "Your submission has been removed for violating Rule 2: Be civil and respectful."
    notification_method: "modmail"  # Optional: use modmail for sensitive issues

  - number: 3
    title: "No NSFW content"
    explanation: "This subreddit is SFW. NSFW content is not allowed."
    response: "Your post has been removed for containing NSFW content, which is not allowed in this community."
```

> Note: The rule `number` field can be either an integer or a string. The system will automatically handle type
> conversion if needed.

## LLM Integration

The tool is designed with a modular approach to LLM integration, allowing easy switching between different providers.

### LLM Prompt Structure

The system constructs a prompt for the LLM that includes:

- The subreddit's rules
- The content to be moderated (submission or comment)
- Instructions for the expected response format

The LLM is expected to return a JSON response with:

```json
{
  "violates": "true|false",
  "rule_number": "<rule number if violated>",
  "explanation": "<explanation of why the rule was violated>",
  "confidence": "<confidence score from 0.0 to 1.0>"
}
```

### Confidence-Based Moderation

The system includes confidence-based moderation to reduce false positives:

- **Confidence Score**: Each LLM decision includes a confidence score (0.0 to 1.0)
- **Threshold Check**: Only decisions with confidence ≥ threshold result in moderation actions
- **Default Behavior**: Low confidence decisions result in "no action" rather than approval
- **Configuration**: Set `llm.confidence_threshold` in `config.yaml` (default: 0.8)

**Example Behavior:**

- High confidence (0.9) + No violation → **Approve**
- Low confidence (0.6) + No violation → **No action** (prevents false approvals)
- High confidence (0.9) + Violation → **Remove**
- Low confidence (0.6) + Violation → **No action** (prevents false removals)

### Adding a New LLM Provider

To implement a new provider:

1. Create a new class in `shared/LLMProvider.py` that inherits from `LLMProvider`
2. Implement the `evaluate_text()` method
3. Add the provider to the `LLMProviderFactory` class
4. Update the configuration format in `config.yaml`

## Troubleshooting

If you encounter issues:

1. Run with the `--debug` flag to get detailed logging:
   ```
   python main.py --mode=cli --subreddit=SUBREDDIT_NAME --debug
   ```

2. Check rule number types in your `rules.yaml` - they should match what the LLM is returning

3. Verify your API credentials in `config.yaml`

4. For connection issues, check your network and API quotas

5. Use the template files as starting points:
   - Copy `config.yaml.template` to `config.yaml`
   - Copy `rules.yaml.template` to `rules.yaml`

6. Check the examples in the `examples/` directory for usage patterns

7. Run tests to verify your setup:
   ```
   python -m pytest tests/
   ```

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines and feel free to submit a Pull Request.

## Documentation

- `README.md` - This file, main project documentation
- `RUNNING.md` - Detailed instructions for running the application
- `CONTRIBUTING.md` - Guidelines for contributing to the project
- `GITHUB.md` - GitHub-specific information and workflows

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
