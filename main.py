#!/usr/bin/env python3
"""
Main entry point for Reddit LLM Moderator CLI.
"""

import logging
import sys
from shared.utils import logger


def main():
    """Launch the CLI moderator."""
    # Import and run CLI mode
    from cli.moderator import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
