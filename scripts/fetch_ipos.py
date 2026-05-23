#!/usr/bin/env python3
"""Fetch IPO activity data from Nasdaq."""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.caching import (
    save_to_json,
    CUSTOM_DATA_DIR,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("fetch_ipos")

# Configuration
CUSTOM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Nasdaq IPO calendar
NASDAQ_IPO_URL = "https://www.nasdaq.com/market-activity/ipos"


def fetch_ipos() -> None:
    """Fetch IPO activity data."""
    logger.info("Fetching IPO activity data...")
    try:
        # Note: Nasdaq IPO data requires web scraping or API access
        # Not implemented - return NA
        ipo_data = {
            "fetch_date": datetime.now().isoformat(),
            "upcoming_ipos": None,
            "recent_ipos": None,
            "source": "Nasdaq",
            "note": "NA - web scraping not implemented",
        }
        
        save_to_json(ipo_data, "ipos", CUSTOM_DATA_DIR)
        logger.info("  Saved IPO data (NA)")
    except Exception as e:
        logger.error(f"  Error fetching IPO data: {e}")
        ipo_data = {
            "fetch_date": datetime.now().isoformat(),
            "upcoming_ipos": None,
            "recent_ipos": None,
            "source": "Nasdaq",
            "note": f"NA - {e}",
        }
        save_to_json(ipo_data, "ipos", CUSTOM_DATA_DIR)


if __name__ == "__main__":
    fetch_ipos()
