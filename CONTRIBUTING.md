# Contributing to Reddit LLM Moderator

Thanks for contributing! This guide covers development setup and the current minimal architecture.

## Development Setup

1. Fork and clone the repository
2. Create a feature branch
3. Install dependencies:
```bash
   uv sync
```
4. Test your changes:
```bash
   uv run main.py --dry-run --debug
```

## Project Structure

```text
reddit-llm-moderator/
├── main.py                 # CLI entrypoint, logging setup
├── openrouter.py           # OpenRouter API integration, prompt building, response parsing
├── moderation.py           # Workflow, Reddit ops, config/rules loading
├── config.yaml.template    # Config template
├── rules.yaml.template     # Rules template
├── pyproject.toml          # Dependencies (praw, pyyaml)
└── .github/
    └── workflows/
        └── moderate.yml    # GitHub Actions workflow
```

## Key Components

### main.py
- CLI entrypoint (~50 lines)
- Argument parsing (--dry-run, --debug, --config, --rules, --log-file)
- Logging configuration
- Calls `moderation.process_modqueue()`

### openrouter.py
- `evaluate(provider_config, item, rules)`: Main entry point, returns a decision dict
- `create_prompt(item, rules)`: Builds LLM prompt (handles both submissions and comments)
- `generate_content(provider_config, prompt)`: HTTP POST to OpenRouter; raises `ProviderError` on 429 or unreachable endpoint, so the caller can stop the run instead of retrying every item
- `parse_response(response)`: JSON parsing + error handling
- `normalize_confidence(raw_value)`: Clamps confidence to 0-100

### moderation.py
- `load_config()`: Loads `config.yaml` (no schema validation — misconfiguration surfaces as an exception at first use)
- `load_rules()`: Loads the `rules` list from `rules.yaml`
- `fetch_modqueue_items()`: Fetches posts and comments, skipping items with any user report or with a prior bot report (matched by `report_marker`), stops at `limit`
- `process_modqueue()`: Main workflow loop; stops early on `ProviderError`
- `process_item(item)`: LLM evaluation + approve/report decision
- `build_report_reason()`: Formats reason with truncation (99 chars max)

## Working with the Code

### Adding a feature

1. Identify which module owns the change (openrouter, moderation, main)
2. Keep changes minimal and focused
3. Test with `--dry-run --debug`
4. Update relevant docs (README, CONTRIBUTING)

### Modifying LLM integration

- Edit `openrouter.py` only (OpenRouter is hardcoded, no factory pattern)
- Update prompt in `create_prompt()` if changing evaluation logic
- Test with actual Reddit modqueue items

### Modifying Reddit operations

- Edit `fetch_modqueue_items()` for fetching behavior
- Edit `process_item()` for approve/report logic
- Edit `build_report_reason()` for reason formatting
- All in `moderation.py`

### Modifying config schema

- Update `load_config()` validation in `moderation.py`
- Update `config.yaml.template`
- Update docs (README)

## Testing

### Dry-run test

```bash
uv run main.py --dry-run --debug
```

Evaluates modqueue, logs decisions, no Reddit actions.

### Single item test

Edit `moderation.py` temporarily to hardcode a test item, then run.

## Pull Request Guidelines

- **Keep it minimal**: Single responsibility per PR
- **Test locally**: Use `--dry-run` first
- **Update docs**: README, CONTRIBUTING if behavior changes
- **Clear message**: Explain what changed and why
- **No dependencies**: Don't add new packages without discussion

## Style Guidelines

- Follow PEP 8
- Keep functions small and focused
- Use type hints where helpful
- Prefer clarity over cleverness
- Comment complex logic

## Architecture Constraints

- **OpenRouter only**: No provider factory, hardcoded (minimalism)
- **Approve + Report only**: No remove action
- **Report filtering**: Skip items already flagged by users, or already reported by this bot
- **Config flat**: No nested providers map, no mode field
- **~500 LOC total**: Keep total codebase small