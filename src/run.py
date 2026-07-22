#!/usr/bin/env python3
"""
Unused Categories Bot for Arabic Wikipedia.

This bot processes unused categories on Arabic Wikipedia by:
1. Fetching unused categories from Arabic Wikipedia's Special:UnusedCategories
2. Finding corresponding categories on English Wikipedia via interwiki links
3. Getting members of the English categories
4. Finding Arabic equivalents of those articles
5. Adding the Arabic category to articles that don't have it

Usage:
    python run.py           # Process all unused categories
    python run.py ask       # Interactive confirmation mode
    python run.py -cat:CategoryName  # Process specific category

Environment Variables:
    WIKIPEDIA_BOT_USERNAME: Wikipedia bot account username
    WIKIPEDIA_BOT_PASSWORD: Wikipedia bot account password

Example:
    Run with interactive confirmation::

        $ python run.py ask

    Process a specific category::

        $ python run.py -cat:تصنيف:أفلام_مغامرات_سويسرية

Notes:
    - Requires a Wikipedia bot account with appropriate permissions
    - Bot edits should comply with Wikipedia's bot policy
    - Use 'ask' mode for testing and review before automated runs

"""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Initialize environment
try:
    load_dotenv()
except Exception:
    logger.warning("load_dotenv error")


def main() -> None:
    """
    Main entry point for the Unused Categories Bot.

    This function:
    1. Parses command-line arguments for mode and category selection
    2. Loads credentials and connects to Wikipedia sites
    3. Fetches unused categories (or uses specified categories)
    4. Processes each category to add it to relevant articles

    Command-line Usage:
        python run.py           # Process all unused categories
        python run.py ask       # Interactive confirmation mode
        python run.py -cat:Cat  # Process specific category

    """
    from src_bot import main_entry

    main_entry()


if __name__ == "__main__":
    main()
