#!/usr/bin/env python3
"""Fetch Supply Chain Pressure Index from NY Federal Reserve."""

import sys
from datetime import datetime
from pathlib import Path

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.caching import (
    CUSTOM_DATA_DIR,
    save_to_json,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("fetch_supply_chain")

# Configuration
CUSTOM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# NY Fed Supply Chain Pressure Index
NY_FED_SCP_URL = "https://www.newyorkfed.org/medialibrary/interactives/supply-chain-pressure-index/data/SCPI.csv"


def fetch_supply_chain() -> None:
    """Fetch supply chain pressure index from NY Fed."""
    logger.info("Fetching NY Fed Supply Chain Pressure Index...")
    try:
        response = requests.get(NY_FED_SCP_URL, timeout=30)
        response.raise_for_status()
        
        # Parse CSV data
        from io import StringIO

        import pandas as pd
        
        df = pd.read_csv(StringIO(response.text))
        if df.empty:
            logger.warning("  No data returned")
            return
        
        # Convert to JSON-serializable format
        data = {
            "fetch_date": datetime.now().isoformat(),
            "latest_index": float(df.iloc[-1, 1]) if len(df.columns) > 1 else None,
            "previous_index": float(df.iloc[-2, 1]) if len(df) > 1 and len(df.columns) > 1 else None,
            "change": None,
            "source": "Federal Reserve Bank of New York",
            "raw_data": df.to_dict(orient="records"),
        }
        
        save_to_json(data, "supply_chain", CUSTOM_DATA_DIR)
        logger.info("  Saved Supply Chain Pressure Index data")
    except Exception as e:
        logger.error(f"  Error fetching Supply Chain data: {e}")
        data = {
            "fetch_date": datetime.now().isoformat(),
            "latest_index": None,
            "previous_index": None,
            "change": None,
            "source": "Federal Reserve Bank of New York",
            "note": f"NA - {e}",
        }
        save_to_json(data, "supply_chain", CUSTOM_DATA_DIR)
        logger.info("  Saved Supply Chain data (NA)")


if __name__ == "__main__":
    fetch_supply_chain()
