#!/usr/bin/env python3
"""Fetch geopolitical risk data from GDELT API."""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.api_keys import get_api_key
from scripts.utils.caching import (
    save_to_json,
    CUSTOM_DATA_DIR,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("fetch_gdelt")

# Configuration
CUSTOM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# GDELT API
GDELT_BASE_URL = "https://api.gdeltproject.org/v2/doc/doc"

# Load API keys
GDELT_API_KEY = get_api_key("GDELT")
if GDELT_API_KEY:
    os.environ["GDELT_API_KEY"] = GDELT_API_KEY
    logger.info(f"GDELT API key configured: {GDELT_API_KEY[:8]}...")
else:
    logger.warning("GDELT API key not found. Using mock data for GDELT.")


def fetch_gdelt() -> None:
    """Fetch geopolitical risk data from GDELT."""
    logger.info("Fetching GDELT geopolitical risk data...")
    
    # Reload key in case it was added
    current_key = get_api_key("GDELT")
    GDELT_API_KEY = current_key
    
    if not GDELT_API_KEY:
        logger.warning("  GDELT API key not found. Using mock data.")
        # Mock data for demo
        gdelt_data = {
            "fetch_date": datetime.now().isoformat(),
            "risk_indicators": {
                "global_risk_index": 65.5,
                "conflict_intensity": "Medium",
                "top_risks": [
                    {"region": "Middle East", "risk_level": 85, "description": "Israel-Hamas conflict"},
                    {"region": "Eastern Europe", "risk_level": 75, "description": "Russia-Ukraine war"},
                    {"region": "South China Sea", "risk_level": 70, "description": "China-US tensions"},
                ],
            },
            "source": "GDELT Project",
            "note": "Actual API requires GDELT API key",
        }
        save_to_json(gdelt_data, "gdelt", CUSTOM_DATA_DIR)
        logger.info("  Saved GDELT data (mock)")
        return
    
    try:
        # Actual API call (requires API key)
        params = {
            "query": "cat:CONFLICT",
            "mode": "artlist",
            "maxrecords": 100,
            "format": "json",
            "api": GDELT_API_KEY,
        }
        response = requests.get(GDELT_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        save_to_json(data, "gdelt", CUSTOM_DATA_DIR)
        logger.info(f"  Saved GDELT data ({len(data)} records)")
    except Exception as e:
        logger.error(f"  Error fetching GDELT: {e}")
        logger.info("  Falling back to mock data")
        gdelt_data = {
            "fetch_date": datetime.now().isoformat(),
            "risk_indicators": {
                "global_risk_index": 65.5,
                "conflict_intensity": "Medium",
                "top_risks": [
                    {"region": "Middle East", "risk_level": 85, "description": "Israel-Hamas conflict"},
                    {"region": "Eastern Europe", "risk_level": 75, "description": "Russia-Ukraine war"},
                    {"region": "South China Sea", "risk_level": 70, "description": "China-US tensions"},
                ],
            },
            "source": "GDELT Project",
            "note": f"API call failed: {e}",
        }
        save_to_json(gdelt_data, "gdelt", CUSTOM_DATA_DIR)
        logger.info("  Saved GDELT data (mock)")


if __name__ == "__main__":
    fetch_gdelt()
