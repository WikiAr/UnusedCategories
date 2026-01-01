# Copilot Instructions for UnusedCategories

This repository contains a Python bot that automatically adds categories to Arabic Wikipedia articles by processing unused categories.

## Project Overview

The bot works by:
1. Fetching unused categories from Arabic Wikipedia
2. Finding their English Wikipedia equivalents via interwiki links
3. Getting members of the English categories
4. Finding Arabic versions of those articles
5. Adding the Arabic category to articles that don't have it yet

## Tech Stack

- **Language**: Python 3.6+
- **Main Library**: mwclient (MediaWiki client library)
- **Environment**: python-dotenv (for loading environment variables)
- **Testing**: pytest (Python standard library)

## Project Structure

- `unused_categories_bot.py` - Main bot implementation
- `test_bot.py` - Unit tests for the bot
- `requirements.txt` - Python dependencies

## Code Conventions

- Use docstrings for all functions with Args, Returns, and Raises sections
- Handle exceptions appropriately, especially for API errors (`mwclient.errors.APIError`, `mwclient.errors.EditError`)
- Use environment variables for credentials (`WM_USERNAME`, `PASSWORD`)
- Arabic category syntax uses `[[تصنيف:CategoryName]]`
- English category syntax uses `[[Category:CategoryName]]`

## Testing

Run tests with:
```bash
python -m pytest test_bot.py
```

Tests are written using Python's pytest framework and do not require a Wikipedia connection.

## Environment Variables

The bot requires the following environment variables:
- `WM_USERNAME`: Wikipedia bot username
- `PASSWORD`: Wikipedia bot password

## Important Notes

- The bot interacts with live Wikipedia sites, so be careful when testing changes
- Category detection is case-insensitive and handles both Arabic (`تصنيف`) and English (`Category`) prefixes
- Edit summaries should be in Arabic (e.g., "بوت: أضاف 1 تصنيف")
