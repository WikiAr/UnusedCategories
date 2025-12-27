# UnusedCategories

A Python bot that automatically adds categories to Arabic Wikipedia articles by processing unused categories.

## Description

This bot helps populate unused categories on Arabic Wikipedia by:

1. Fetching unused categories from Arabic Wikipedia
2. Finding their English Wikipedia equivalents
3. Getting members of the English categories
4. Finding Arabic versions of those articles
5. Adding the Arabic category to articles that don't have it yet

## Requirements

- Python 3.6+
- mwclient library

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set the following environment variables:

- `WM_USERNAME`: Your Wikipedia bot username
- `PASSWORD`: Your Wikipedia bot password

Example:
```bash
export WM_USERNAME="YourBotName@YourBotPassword"
export PASSWORD="your_bot_password_token"
```

## Usage

```bash
python unused_categories_bot.py
```

## How it works

```
Start
  ↓
Load credentials from environment variables
  ↓
Connect to Arabic Wikipedia using mwclient
  ↓
Fetch unusedcategories list
  ↓
For each category:
  ↓
  Get English Wikipedia link of category 
  ↓
  Get English category members
  ↓
  For each member article:
    ↓
    Get Arabic Wikipedia link
    ↓
    Search for the Arabic category in text
    ↓
    Not Found in text?
    ├─ Add it to the bottom of the text and save it with summary "بوت: أضاف 1 تصنيف"
  ↓
End
```

## Features

- Automatically skips articles that already have the category
- Uses proper Arabic category syntax (`[[تصنيف:CategoryName]]`)
- Includes error handling for network issues and missing interwiki links
- Provides detailed logging of all operations

## License

This project is open source and available under the MIT License.
