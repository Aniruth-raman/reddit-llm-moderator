# Contributing to Reddit LLM Moderator

Thank you for considering contributing to Reddit LLM Moderator! This document provides guidelines and instructions for contribution.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming environment.

## Ways to Contribute

- Report bugs
- Suggest new features or enhancements
- Improve documentation
- Submit pull requests to fix issues or add features

## Development Setup

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/reddit-llm-moderator.git
   cd reddit-llm-moderator
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov flake8
   ```
5. Make your changes
6. Run the tests and linting:
   ```bash
   pytest
   flake8
   ```

## Project Structure

```
reddit-llm-moderator/
├── main.py                # Main entry point for both CLI and MCP modes
├── cli/                   # Command-line interface implementation
│   └── reddit_mod.py      # CLI-specific code
├── mcp/                   # Model Context Protocol server implementation
│   └── server.py          # FastAPI server for the MCP implementation
└── shared/                # Shared code used by both CLI and MCP
    ├── llm_core.py        # LLM provider implementations
    ├── models.py          # Data models for the application
    ├── moderation.py      # Moderation service and strategies
    └── utils.py           # Utility functions
```

## Adding a New LLM Provider

1. Implement the provider in `shared/llm_core.py` by adding a new class that inherits from `LLMProvider`
2. Implement the `evaluate_text()` method
3. Add the provider to the `LLMProviderFactory` class
4. Update the configuration format in `config.yaml`
5. Add tests for your new provider

## Pull Request Process

1. Update documentation as needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update the README.md if needed
5. Submit a pull request with a clear description of the changes

## Style Guidelines

- Follow PEP 8 style guide
- Use clear, descriptive variable and function names
- Add docstrings to all functions, classes, and modules
- Keep functions focused on a single responsibility
- Write meaningful commit messages

## Testing

- All new features should have corresponding tests
- Run the test suite before submitting a pull request
- Aim for good test coverage of your code

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
