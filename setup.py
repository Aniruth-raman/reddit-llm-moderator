#!/usr/bin/env python3
"""
Setup script for Reddit LLM Moderator.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="reddit-llm-moderator",
    version="0.1.0",
    author="Reddit LLM Moderator Developers",
    author_email="your.email@example.com",    description="A tool that uses LLMs to help moderate Reddit submissions and comments based on subreddit rules",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Aniruth-raman/reddit-llm-moderator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Communications",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "reddit-llm-mod=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml"],
    },
)
