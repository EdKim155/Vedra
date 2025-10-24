#!/usr/bin/env python3
"""
Script to run the Cars Telegram Bot.

Usage:
    python scripts/run_bot.py
    or
    make run-bot
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment variables before importing settings
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from cars_bot.config import init_settings
from cars_bot.bot import run

if __name__ == "__main__":
    # Initialize settings
    init_settings()
    
    # Run bot
    run()

