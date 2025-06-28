# Running Reddit LLM Moderator

This guide provides instructions for setting up and running the Reddit LLM Moderator in both CLI and MCP server modes.

## Prerequisites

- Python 3.9 or higher
- Reddit API credentials (client ID, client secret, username, password)
- API key for at least one LLM provider (OpenAI, Anthropic, Google Gemini, or Ollama installed locally)

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/Aniruth-raman/reddit-llm-moderator.git
   cd reddit-llm-moderator
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the application:
   ```bash
   cp config.yaml.template config.yaml
   # Edit config.yaml with your API credentials
   ```

4. Configure your subreddit rules:
   ```bash
   cp rules.yaml.template rules.yaml
   # Edit rules.yaml to match your subreddit's rules
   ```

## Confidence Threshold Configuration

The moderator uses confidence scores to make more reliable decisions:

- Set `llm.confidence_threshold` in `config.yaml` (default: 0.8)
- Only actions with confidence ≥ threshold will be taken
- Low confidence results in "no action" instead of potentially incorrect moderation
- This prevents false positives and makes the system more conservative

Example in `config.yaml`:
```yaml
llm:
  confidence_threshold: 0.8  # Only act when AI is 80%+ confident
```

## Using the CLI Mode

The CLI mode allows you to process your modqueue items directly from the command line.

### Basic Usage

```bash
python main.py --mode=cli --subreddit=SUBREDDIT_NAME
```

### Options

- `--subreddit`, `-s`: Subreddit to moderate (required)
- `--dry-run`, `-d`: Simulate actions without taking them
- `--config`, `-c`: Path to config file (default: config.yaml)
- `--rules`, `-r`: Path to rules file (default: rules.yaml)
- `--type`, `-t`: Type of modqueue items to process (`all`, `submissions`, or `comments`)
- `--debug`: Enable debug logging for troubleshooting
- `--notification`: How to deliver removal reasons (`public` or `modmail`)

### Examples

Process all modqueue items in your subreddit:
```bash
python main.py --mode=cli --subreddit=MySubreddit
```

Process only comments, sending removal reasons via modmail:
```bash
python main.py --mode=cli --subreddit=MySubreddit --type=comments --notification=modmail
```

Simulate moderation of submissions only with debug output:
```bash
python main.py --mode=cli --subreddit=MySubreddit --type=submissions --dry-run --debug
```

## Using the MCP Server Mode

The MCP server mode provides a REST API for programmatic access to the moderation functionality.

### Starting the Server

```bash
python main.py --mode=mcp
```

The server will start on port 8000 by default. You can access the API documentation at `http://localhost:8000/docs`.

### API Endpoints

- `POST /initialize`: Initialize the server with config and rules
- `GET /modqueue`: Get items from the modqueue
- `POST /moderate`: Moderate a specific item
- `GET /rules`: Get the configured rules

### Example API Usage

Initialize the server:
```bash
curl -X POST "http://localhost:8000/initialize" \
     -H "Content-Type: application/json" \
     -d '{"config_path": "config.yaml", "rules_path": "rules.yaml"}'
```

Get modqueue items:
```bash
curl -X GET "http://localhost:8000/modqueue?subreddit=MySubreddit&limit=10&item_type=all"
```

Moderate a specific item:
```bash
curl -X POST "http://localhost:8000/moderate" \
     -H "Content-Type: application/json" \
     -d '{"subreddit": "MySubreddit", "item_id": "abc123", "dry_run": true, "notification_method": "public"}'
```

## Using the Example Client

For an example of how to use the MCP API programmatically, see the Python client in `examples/mcp_client.py`:

```bash
python examples/mcp_client.py --subreddit=MySubreddit --dry-run
```

## Troubleshooting

If you encounter issues:

1. Run with the `--debug` flag to get detailed logging:
   ```bash
   python main.py --mode=cli --subreddit=SUBREDDIT_NAME --debug
   ```

2. Check your API credentials in config.yaml

3. Verify that your rules.yaml is properly formatted

4. For MCP server issues, check the server logs and ensure the initialization endpoint was called successfully
