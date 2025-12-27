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

### Interactive Confirmation Mode

Run with the `ask` argument to enable interactive confirmation mode. In this mode, the bot will ask for confirmation before each edit:

```bash
python unused_categories_bot.py ask
```

When prompted, you can respond with:
- **Empty** or **y** or **yes**: Approve this edit and continue asking for the next one
- **n** or **no**: Skip this edit and continue to the next one
- **a**: Approve all remaining edits without asking again

## How it works

```
Start
  ↓
Fetch unused Arabic categories
  ↓
For each Arabic category:
  ↓
  Filter Arabic category:
    - hidden?
    - maintenance (صيانة)?
    - stub (بذور)?
    - starts with بذرة?
  ↓ (Skip if any true)
  ↓
  Get English interwiki link
  ↓ (Skip if not found)
  ↓
  Filter English category:
    - hidden?
    - maintenance?
    - stub?
  ↓ (Skip if any true)
  ↓
  Get English category members
  ↓
  For each English article:
    ↓
    Load English wikitext
    ↓
    Category explicitly present in text?
        ├─ No → Skip article (category added via template)
    ↓
    Get Arabic interwiki link
        ├─ No → Skip article
    ↓
    Load Arabic article text
    ↓
    Arabic category already exists?
        ├─ Yes → Skip
        ├─ No → Append category and save with summary "بوت: أضاف 1 تصنيف"
  ↓
End
```

## Features

- Automatically skips articles that already have the category
- Filters out hidden categories (both Arabic and English)
- Filters out maintenance categories (صيانة in Arabic, "maintenance" in English)
- Filters out stub categories (بذور/بذرة in Arabic, "stub" in English)
- Only processes articles where the category is explicitly in the text (not added via templates)
- Uses proper Arabic category syntax (`[[تصنيف:CategoryName]]`)
- Includes error handling for network issues and missing interwiki links
- Provides detailed logging of all operations

## License

This project is open source and available under the MIT License.
