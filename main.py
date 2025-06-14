#!/usr/bin/env python3
"""
Main entry point for Reddit LLM Moderator.
"""

import argparse
import sys

def main():
    """Process command line arguments and launch the appropriate mode."""
    parser = argparse.ArgumentParser(description="Reddit LLM Moderator")
    parser.add_argument(
        "--mode", "-m",
        choices=["cli", "mcp"],
        default="cli",
        help="Operation mode: cli (Command Line Interface) or mcp (Model Context Protocol server)"
    )
    
    # Parse just the mode argument first
    args, remaining = parser.parse_known_args()
    
    if args.mode == "cli":
        # Import and run CLI mode
        from cli.reddit_mod import main as cli_main
        sys.argv = [sys.argv[0]] + remaining
        cli_main()
    elif args.mode == "mcp":
        # Import and run MCP server mode
        from mcp.server import start_server
        start_server()
    else:
        print(f"Unknown mode: {args.mode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
