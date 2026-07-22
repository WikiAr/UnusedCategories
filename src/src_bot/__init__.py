from __future__ import annotations

import logging
import sys
from pathlib import Path

from .entry_bot import main_entry
from .logging_config import setup_logging

level = "DEBUG" if ("debug" in sys.argv or "DEBUG" in sys.argv) else "INFO"
print(f"{level=}")
setup_logging(name=Path(__file__).parent.name, level=level)

logger = logging.getLogger(__name__)

__all__ = [
    "main_entry",
]
