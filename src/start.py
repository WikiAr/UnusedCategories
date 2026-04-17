#!/usr/bin/env python3
"""
Unused Categories Bot for Arabic Wikipedia.
"""

from __future__ import annotations

import logging
import sys

from .unused_categories_bot import (
    is_credentials_loaded,
    set_ask_mode,
    start_work,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Main Entry Point
# =============================================================================


def parse_category_args() -> list[str]:
    """
    Parse command-line arguments for specific categories.

    Looks for arguments in the format -cat:CategoryName and extracts
    the category names. Underscores in the argument are replaced with spaces.

    Returns:
        A list of category names specified on the command line.

    Example:
        Command line: python bot.py -cat:تصنيف:علوم -cat:Category:Science
        Returns: ["تصنيف:علوم", "Category:Science"]

    """
    categories: list[str] = []

    for arg in sys.argv:
        arg_key, _, value = arg.partition(":")
        if arg_key == "-cat" and value:
            # Replace underscores with spaces for wiki compatibility
            categories.append(value.replace("_", " "))

    return categories


def main_entry() -> None:
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

    # Check for "ask" argument to enable interactive confirmation mode
    if "ask" in sys.argv:
        set_ask_mode(True)
        logger.info("Interactive confirmation mode enabled.")

    logger.info("Starting Unused Categories Bot for Arabic Wikipedia")
    logger.info("=" * 60)

    if not is_credentials_loaded():
        sys.exit(1)

    # Get categories to process
    unused_categories = parse_category_args()

    start_work(unused_categories)
    logger.info("=" * 60)
