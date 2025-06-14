<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Reddit Moderation CLI Tool

This project is a Python CLI tool that uses PRAW (Python Reddit API Wrapper) and an LLM (like OpenAI) to moderate Reddit submissions in a modqueue based on subreddit rules.

Key components:
- Authentication with Reddit using script credentials
- Loading subreddit rules from a YAML file
- Fetching items from the modqueue
- Using LLM to evaluate submissions against rules
- Taking moderation actions based on LLM decisions
