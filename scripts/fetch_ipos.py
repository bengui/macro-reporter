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
        # For demo, use mock data
        ipo_data = {
            "fetch_date": datetime.now().isoformat(),
            "upcoming_ipos": [
                {"company": "TechCorp Inc.", "symbol": "TCI", "price_range": "$18-$20", "shares": 10000000, "date": "2026-05-20"},
                {"company": "BioHealth Ltd.", "symbol": "BHL", "price_range": "$14-$16", "shares": 8000000, "date": "2026-05-25"},
                {"company": "GreenEnergy Co.", "symbol": "GEC", "price_range": "$25-$28", "shares": 12000000, "date": "2026-06-01"},
            ],
            "recent_ipos": [
                {"company": "CloudFirst", "symbol": "CFST", "price": "$22", "shares": 15000000, "date": "2026-04-15", "performance": "+15%"},
                {"company": "DataSystems", "symbol": "DSYS", "price": "$18", "shares": 10000000, "date": "2026-04-10", "performance": "+8%"},
            ],
            "source": "Nasdaq",
            "note": "Mock data - actual scraping would be required for production",
        }
        
        save_to_json(ipo_data, "ipos", CUSTOM_DATA_DIR)
        logger.info("  Saved IPO data (mock)")
    except Exception as e:
        logger.error(f"  Error fetching IPO data: {e}")


if __name__ == "__main__":
    fetch_ipos()
