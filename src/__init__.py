from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv  # type: ignore

logger = logging.getLogger(__name__)

try:
    load_dotenv(str(Path(__file__).parent / ".env"))
except Exception as e:
    logger.error(f"Error loading .env file: {e}")
