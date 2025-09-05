# Reddit LLM Moderator

A clean, minimal Python tool that uses LLM evaluation to help moderate Reddit content based on subreddit rules.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Minimal architecture** - Just 3 files with clean separation of concerns
- **Extensible LLM support** - Currently supports Google Gemini with easy extensibility for other providers
- **SOLID principles** - Follows clean code principles and design patterns
- **Reddit integration** - Authentication with Reddit using PRAW
- **Rule-based moderation** - Load subreddit rules from YAML configuration
- **Structured LLM evaluation** - JSON-based responses with confidence scoring
- **Threshold-based actions** - Configurable confidence thresholds for approve/remove decisions
- **Robust JSON parsing** - Advanced fallback parsing for LLM responses with automatic confidence scaling
- **Dry-run mode** - Test the system without taking actual moderation actions
- **Comprehensive logging** - Debug and info logging with file output support
- **Command-line interface** - Rich CLI with multiple options for different use cases

## Architecture

The tool follows clean architecture principles with perfect separation of concerns:

```
reddit-llm-moderator/
├── main.py              # Main orchestration and application entry point (85 lines)
├── llm_eval.py         # LLM evaluation with extensible provider support (145 lines)  
├── reddit_ops.py       # Reddit operations using PRAW (81 lines)
├── requirements.txt    # Minimal dependencies (3 packages)
├── config.yaml.template # Configuration template with extensible options
└── rules.yaml.template # Rules configuration template
```

**Total: 311 lines of clean, maintainable code**

### Key Design Patterns

- **Factory Pattern**: `LLMProviderFactory` for creating LLM providers
- **Strategy Pattern**: `LLMProvider` abstract base class for different providers  
- **Dependency Injection**: Clear separation of concerns with dependency injection
- **Single Responsibility**: Each class/module has one clear purpose

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

### CLI Commands

Basic usage:

```bash
python main.py
```

All available options:

```bash
python main.py [--dry-run] [--debug] [--log-file LOG_FILE] [--config CONFIG] [--rules RULES]
```

### Command Line Options

- `--dry-run`: Run in dry-run mode (show suggestions without taking action)
- `--debug`: Enable debug logging for detailed troubleshooting
- `--log-file LOG_FILE`: Save logs to specified file (optional)
- `--config CONFIG`: Configuration file path (default: config.yaml)
- `--rules RULES`: Rules file path (default: rules.yaml)

### Examples

```bash
# Basic moderation run
python main.py

# Dry run to see what would be moderated without taking action
python main.py --dry-run

# Enable debug logging to console
python main.py --debug

# Save logs to file with debug information
python main.py --debug --log-file moderation.log

# Use custom config and rules files
python main.py --config my_config.yaml --rules my_rules.yaml

# Dry run with debug logging saved to file
python main.py --dry-run --debug --log-file dry_run.log
```

## Configuration Files

### config.yaml

Example configuration (copy from `config.yaml.template` and fill in your values):

```yaml
# Reddit API Configuration
reddit:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET" 
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  user_agent: "RedditModerator/1.0 by YourUsername"
  subreddit: "YourSubreddit"

# Moderation thresholds
approve_threshold: 80  # Confidence % required to approve (0-100)
remove_threshold: 70   # Confidence % required to remove (0-100)

# LLM Provider Configuration
llm_provider:
  provider: "gemini"  # Currently supported: gemini
  api_key: "YOUR_GEMINI_API_KEY"
  model: "gemini-1.5-pro"
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
  "violates": true,
  "rule_number": 1,
  "explanation": "explanation of why the rule was violated",
  "confidence": 0.85
}
```

### Robust JSON Parsing

The system includes advanced JSON parsing capabilities:

- **Primary Parsing**: Direct JSON parsing for well-formed responses
- **Regex Fallback**: Extracts JSON from text with extra content using `\{.*\}` pattern  
- **Automatic Confidence Scaling**: Converts confidence from 0.0-1.0 scale to 0-100 scale automatically
- **Error Handling**: Graceful degradation with detailed error messages

### Confidence-Based Moderation

The system uses confidence thresholds (0-100 scale) for moderation decisions:

- **approve_threshold**: Minimum confidence % required to approve content (default: 80)
- **remove_threshold**: Minimum confidence % required to remove content (default: 70)
- **Skip logic**: Content with confidence below thresholds is skipped (no action taken)

**Example Behavior:**

- High confidence (85%) + No violation → **Approve** (if ≥ approve_threshold)
- Low confidence (60%) + No violation → **Skip** (prevents false approvals)
- High confidence (90%) + Violation → **Remove** (if ≥ remove_threshold)
- Low confidence (65%) + Violation → **Skip** (prevents false removals)

### Adding a New LLM Provider

To implement a new provider:

1. Create a new class in `llm_eval.py` that inherits from `LLMProvider`
2. Implement the `evaluate()` and `_generate_content()` methods
3. Add the provider to the `LLMProviderFactory.create_provider()` method
4. Update the configuration format in `config.yaml.template`

Example:

```python
class OpenAIProvider(LLMProvider):
    def __init__(self, config):
        # Initialize OpenAI client
        pass
    
    def _generate_content(self, prompt):
        # Call OpenAI API
        pass
    
    # evaluate() method is inherited and handles prompt creation + parsing
```

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
