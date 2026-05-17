#!/usr/bin/env python3
"""
Fetch financial data from OpenBB.

This script fetches market indices, commodities, forex, macroeconomic indicators,
bonds/yields, and news data using the OpenBB library.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports - MUST BE BEFORE other imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set API keys as environment variables BEFORE importing obb
# This is required for OpenBB to pick them up
from scripts.utils.api_keys import get_api_key

FRED_KEY = get_api_key("FRED")
if FRED_KEY:
    os.environ["FRED_API_KEY"] = FRED_KEY

FMP_KEY = get_api_key("FMP")
if FMP_KEY:
    os.environ["FMP_API_KEY"] = FMP_KEY

GDELT_KEY = get_api_key("GDELT")
if GDELT_KEY:
    os.environ["GDELT_API_KEY"] = GDELT_KEY

from openbb import obb

from scripts.utils.caching import (
    save_to_csv,
    OPENBB_DATA_DIR,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("fetch_openbb")

# Log API key status
if FRED_KEY:
    logger.info(f"FRED API key configured: {FRED_KEY[:8]}...")
else:
    logger.warning("FRED API key not found. Some data may be unavailable.")

if FMP_KEY:
    logger.info(f"FMP API key configured")

if GDELT_KEY:
    logger.info(f"GDELT API key configured")


# Configuration
START_DATE = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

# Market indices symbols - using equity.price.historical which works without API keys
MARKET_INDICES = {
    "sp500": "^GSPC",
    "stoxx600": "^STOXX50E",  # STOXX Europe 50 (more available)
    "msci_world": "URTH",  # iShares MSCI World ETF
    "vix": "^VIX",
}

# Commodities symbols - using equity.price.historical as fallback
COMMODITIES = {
    "gold": "GC=F",
    "brent_crude": "BZ=F",
    "copper": "HG=F",
    "wheat": "ZW=F",
}

# Forex pairs - using equity.price.historical with =X suffix
FOREX_PAIRS = {
    "usd_eur": "EUR=X",
    "usd_cny": "USDCNY=X",
    # DXY (US Dollar Index) requires API key, skipping for now
}

# Macroeconomic indicators - using obb.economy methods
MACRO_INDICATORS = {
    "us_cpi": {"method": "cpi", "country": "united_states"},  # US CPI
    "us_unemployment": {"method": "unemployment", "country": "united_states"},  # US Unemployment Rate
    # Euro Area / EU data
    "eu_cpi": {"method": "cpi", "country": "euro_area", "harmonized": True, "provider": "imf"},  # EU CPI
    "eu_unemployment": {"method": "unemployment", "country": "european_union27_2020"},  # EU Unemployment
    # Spain data
    "spain_cpi": {"method": "cpi", "country": "spain"},  # Spain CPI
    "spain_unemployment": {"method": "unemployment", "country": "spain"},  # Spain Unemployment
    # GDP uses fred_series directly since gdp() is not callable
}

# Additional macro indicators using FRED directly
# Note: FRED data is often quarterly, so we use a longer start date
FRED_START_DATE = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")  # 5 years

FRED_INDICATORS = {
    "us_gdp": "GDP",  # US GDP (nominal)
    "us_gdp_real": "GDPC1",  # US Real GDP
    "us_debt_to_gdp": "FYGFDPUN",  # US Federal Debt to GDP ratio
}

# Government debt to GDP from country_profile (uses OpenBB which may use FRED/other sources)
# These are fetched separately as they use country_profile method
GOVT_DEBT_COUNTRIES = [
    "united_states",  # US - uses country_profile
    "euro_area",      # EU - uses country_profile  
    "spain",          # Spain - uses country_profile
]

# Bonds - using fixedincome.government.treasury_rates which works without API keys
BONDS = {
    "us_treasury_rates": "treasury_rates",  # All US Treasury rates
}


def fetch_market_indices() -> None:
    """Fetch market indices data using equity.price.historical."""
    logger.info("Fetching market indices...")
    for name, symbol in MARKET_INDICES.items():
        try:
            logger.info(f"  Fetching {name} ({symbol})...")
            data = obb.equity.price.historical(
                symbol=symbol,
                start_date=START_DATE,
            ).to_df()
            if data.empty:
                logger.warning(f"  No data returned for {name}")
                continue
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.error(f"  Error fetching {name}: {e}")


def fetch_commodities() -> None:
    """Fetch commodities data using equity.price.historical."""
    logger.info("Fetching commodities...")
    for name, symbol in COMMODITIES.items():
        try:
            logger.info(f"  Fetching {name} ({symbol})...")
            data = obb.equity.price.historical(
                symbol=symbol,
                start_date=START_DATE,
            ).to_df()
            if data.empty:
                logger.warning(f"  No data returned for {name}")
                continue
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.error(f"  Error fetching {name}: {e}")


def fetch_forex() -> None:
    """Fetch forex data using equity.price.historical with =X suffix."""
    logger.info("Fetching forex rates...")
    for name, symbol in FOREX_PAIRS.items():
        try:
            logger.info(f"  Fetching {name} ({symbol})...")
            data = obb.equity.price.historical(
                symbol=symbol,
                start_date=START_DATE,
            ).to_df()
            if data.empty:
                logger.warning(f"  No data returned for {name}")
                continue
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.error(f"  Error fetching {name}: {e}")


def fetch_macroeconomics() -> None:
    """Fetch macroeconomic data using obb.economy methods."""
    logger.info("Fetching macroeconomic indicators...")
    for name, config in MACRO_INDICATORS.items():
        try:
            logger.info(f"  Fetching {name}...")
            method_name = config["method"]
            country = config.get("country", "united_states")
            harmonized = config.get("harmonized", False)
            provider = config.get("provider", None)
            
            method = getattr(obb.economy, method_name)
            kwargs = {"country": country, "harmonized": harmonized}
            if provider:
                kwargs["provider"] = provider
            data = method(**kwargs).to_df()
            
            if data.empty:
                logger.warning(f"  No data returned for {name}")
                continue
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.error(f"  Error fetching {name}: {e}")


def fetch_fred_indicators() -> None:
    """Fetch indicators directly from FRED."""
    logger.info("Fetching FRED indicators...")
    for name, series_id in FRED_INDICATORS.items():
        try:
            logger.info(f"  Fetching {name} ({series_id})...")
            data = obb.economy.fred_series(
                symbol=series_id,
                start_date=FRED_START_DATE,
            ).to_df()
            
            if data.empty:
                logger.warning(f"  No data returned for {name}")
                continue
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.error(f"  Error fetching {name}: {e}")


def fetch_bonds() -> None:
    """Fetch bonds/yields data using fixedincome.government.treasury_rates."""
    logger.info("Fetching bonds data...")
    for name, method_name in BONDS.items():
        try:
            logger.info(f"  Fetching {name}...")
            if method_name == "treasury_rates":
                data = obb.fixedincome.government.treasury_rates().to_df()
            else:
                logger.warning(f"  Unknown method: {method_name}")
                continue
            
            if data.empty:
                logger.warning(f"  No data returned for {name}")
                continue
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.error(f"  Error fetching {name}: {e}")


def fetch_govt_debt_to_gdp() -> None:
    """Fetch government debt to GDP ratio from country profiles."""
    logger.info("Fetching government debt to GDP ratios...")
    
    # Map country codes to file names
    country_to_name = {
        "united_states": "us_debt_to_gdp",
        "euro_area": "eu_debt_to_gdp",
        "spain": "spain_debt_to_gdp",
    }
    
    for country in GOVT_DEBT_COUNTRIES:
        try:
            name = country_to_name.get(country, f"{country}_debt_to_gdp")
            logger.info(f"  Fetching {name}...")
            
            data = obb.economy.country_profile(country=country).to_df()
            
            if data.empty or "govt_debt_gdp" not in data.columns:
                logger.warning(f"  No govt_debt_gdp data for {country}")
                continue
            
            # Reset index to include date as a column
            data = data.reset_index()
            save_to_csv(data, name, OPENBB_DATA_DIR)
            logger.info(f"  Saved {name} data ({len(data)} rows)")
        except Exception as e:
            logger.warning(f"  Could not fetch debt to GDP for {country}: {e}")


def fetch_news() -> None:
    """Fetch financial news - requires API keys, skip for now."""
    logger.info("Fetching news...")
    try:
        # Market news requires API keys for most providers
        # Skipping for now as it requires credentials
        logger.info("  Skipping news (requires API keys)")
    except Exception as e:
        logger.error(f"  Error fetching news: {e}")


def fetch_all() -> None:
    """Fetch all data from OpenBB."""
    logger.info("=" * 60)
    logger.info("Starting OpenBB data fetch")
    logger.info(f"  Start date: {START_DATE}")
    logger.info("=" * 60)
    
    fetch_market_indices()
    fetch_commodities()
    fetch_forex()
    fetch_macroeconomics()
    fetch_fred_indicators()
    fetch_govt_debt_to_gdp()
    fetch_bonds()
    fetch_news()
    
    logger.info("=" * 60)
    logger.info("OpenBB data fetch completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    fetch_all()
