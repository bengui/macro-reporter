#!/usr/bin/env python3
"""
Fetch data from custom APIs (Iteration 2).

This script fetches Euribor rates, geopolitical risk data, supply chain pressure,
and IPO activity from custom APIs. Also fetches additional ECB data for enhanced reports.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.api_keys import get_api_key
from scripts.utils.caching import (
    save_to_json,
    CUSTOM_DATA_DIR,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("fetch_custom")

# Configuration
CUSTOM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ECB Data Portal API configuration
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# Load API keys
GDELT_API_KEY = get_api_key("GDELT")
if GDELT_API_KEY:
    os.environ["GDELT_API_KEY"] = GDELT_API_KEY
    logger.info(f"GDELT API key configured: {GDELT_API_KEY[:8]}...")
else:
    logger.warning("GDELT API key not found. Using mock data for GDELT.")

FMP_KEY = get_api_key("FMP")
if FMP_KEY:
    os.environ["FMP_API_KEY"] = FMP_KEY
    logger.info(f"FMP API key configured")

ECB_KEY = get_api_key("ECB")
if ECB_KEY:
    os.environ["ECB_API_KEY"] = ECB_KEY
    logger.info(f"ECB API key configured")


def fetch_ecb_series(
    dataflow: str,
    series_key: str,
    last_n: int = 1,
    timeout: int = 30
) -> Optional[dict]:
    """
    Fetch a single series from ECB Data Portal API.
    
    Args:
        dataflow: Dataflow ID (e.g., 'YC', 'EXR', 'FM')
        series_key: Series key within the dataflow
        last_n: Number of most recent observations to return
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with latest value or None if error
    """
    url = f"{ECB_API_BASE}/{dataflow}/{series_key}"
    params = {
        "format": "jsondata",
        "lastNObservations": str(last_n),
    }
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code != 200:
            logger.warning(f"  ECB API returned {response.status_code} for {dataflow}/{series_key}")
            return None
        
        data = json.loads(response.text)
        
        # Extract the latest value
        if "dataSets" not in data or not data["dataSets"]:
            return None
        
        dataset = data["dataSets"][0]
        if "series" not in dataset:
            return None
        
        series = list(dataset["series"].values())[0]
        if "observations" not in series or not series["observations"]:
            return None
        
        observations = series["observations"]
        latest_time = max(observations.keys())
        latest_value = observations[latest_time][0]
        
        if latest_value is None:
            return None
        
        try:
            return {
                "value": float(latest_value),
                "time": latest_time,
                "raw_data": data,
            }
        except (ValueError, TypeError) as e:
            logger.warning(f"  Could not parse value for {dataflow}/{series_key}: {e}")
            return None
            
    except Exception as e:
        logger.warning(f"  Error fetching {dataflow}/{series_key}: {e}")
        return None

# GDELT API
GDELT_BASE_URL = "https://api.gdeltproject.org/v2/doc/doc"

# NY Fed Supply Chain Pressure Index
NY_FED_SCP_URL = "https://www.newyorkfed.org/medialibrary/interactives/supply-chain-pressure-index/data/SCPI.csv"

# Nasdaq IPO calendar
NASDAQ_IPO_URL = "https://www.nasdaq.com/market-activity/ipos"


def fetch_euribor() -> None:
    """Fetch Euribor rates from ECB Data Portal API.
    
    Uses the ECB's Data Portal API which requires no API key.
    The ECB publishes daily Euribor rates via SDMX-ML web service.
    API docs: https://data.ecb.europa.eu/help/api/data
    """
    logger.info("Fetching Euribor rates from ECB Data Portal...")
    
    # ECB Data Portal API base URL
    base_url = "https://data-api.ecb.europa.eu/service/data"
    
    # Series keys for Euribor rates from FM (Financial Market data) dataflow
    # The dataflow is FM, and the series keys (from CSV output) are like:
    # FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA
    # So for the API URL, we use: data/FM/M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA
    # Tenor codes: 1WD (1 week), 1MD (1 month), 3MD (3 months), 6MD (6 months), 1YD (1 year)
    euribor_series = {
        "EURIBOR_1W": "M.U2.EUR.RT.MM.EURIBOR1WD_.HSTA",
        "EURIBOR_1M": "M.U2.EUR.RT.MM.EURIBOR1MD_.HSTA",
        "EURIBOR_3M": "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
        "EURIBOR_6M": "M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA",
        "EURIBOR_12M": "M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA",
    }
    
    rates = {}
    
    for tenor, series_key in euribor_series.items():
        try:
            # Build API URL
            url = f"{base_url}/FM/{series_key}?format=jsondata&lastNObservations=1"
            logger.info(f"  Fetching {tenor} from {url}")
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                import json
                data = json.loads(response.text)
                
                # Extract the latest observation
                if 'dataSets' in data and len(data['dataSets']) > 0:
                    series_data = data['dataSets'][0]['series']
                    for key, value in series_data.items():
                        if 'observations' in value:
                            # Get the most recent observation
                            obs = value['observations']
                            if obs:
                                # Sort by time period and get latest
                                latest_time = max(obs.keys())
                                rate_value = obs[latest_time][0]
                                if rate_value is not None:
                                    try:
                                        rates[tenor] = float(rate_value)
                                        logger.info(f"  {tenor}: {rate_value}")
                                        break
                                    except (ValueError, TypeError):
                                        logger.warning(f"  Could not parse {tenor}: {rate_value}")
            else:
                logger.warning(f"  {tenor} returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"  Error fetching {tenor}: {e}")
    
    if rates:
        euribor_data = {
            "fetch_date": datetime.now().isoformat(),
            "rates": rates,
            "source": "ECB Data Portal API (FM dataflow)",
        }
        save_to_json(euribor_data, "euribor", CUSTOM_DATA_DIR)
        logger.info(f"  Saved Euribor data ({len(rates)} rates)")
    else:
        # Fallback to mock data - ECB rates as of recent data
        logger.warning("  Could not fetch from ECB API. Using recent mock data.")
        euribor_data = {
            "fetch_date": datetime.now().isoformat(),
            "rates": {
                "EURIBOR_1W": 3.85,
                "EURIBOR_1M": 3.87,
                "EURIBOR_3M": 3.90,
                "EURIBOR_6M": 3.92,
                "EURIBOR_12M": 3.95,
            },
            "source": "Mock data (based on recent ECB rates)",
            "note": "ECB API was unreachable. Data reflects approximate recent rates.",
        }
        save_to_json(euribor_data, "euribor", CUSTOM_DATA_DIR)
        logger.info("  Saved Euribor data (mock)")


def fetch_ecb_yield_curve() -> None:
    """Fetch Euro area government bond yield curve from ECB."""
    logger.info("Fetching ECB yield curve data...")
    
    # Yield curve maturities - using working series keys
    # Format: YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_{MATURITY}
    # But API needs just the key part after dataflow: B.U2.EUR.4F.G_N_C.SV_C_YM.SR_{MATURITY}
    yield_series = {
        "2Y": "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_2Y",
        "5Y": "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_5Y",
        "10Y": "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y",
        "30Y": "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_30Y",
    }
    
    yields = {}
    for maturity, series_key in yield_series.items():
        result = fetch_ecb_series("YC", series_key, last_n=1)
        if result and "value" in result:
            yields[maturity] = result["value"]
            logger.info(f"  {maturity}: {result['value']}%")
        else:
            logger.warning(f"  Could not fetch {maturity} yield")
    
    if yields:
        yield_data = {
            "fetch_date": datetime.now().isoformat(),
            "yields": yields,
            "source": "ECB Data Portal API (YC dataflow)",
        }
        save_to_json(yield_data, "ecb_yield_curve", CUSTOM_DATA_DIR)
        logger.info(f"  Saved yield curve data ({len(yields)} maturities)")
    else:
        logger.warning("  No yield curve data fetched. Skipping.")


def fetch_ecb_reference_rates() -> None:
    """Fetch ECB reference rates (€STR, EONIA) from ECB."""
    logger.info("Fetching ECB reference rates...")
    
    # Series keys for reference rates
    reference_series = {
        "ESTR": "M.U2.EUR.4F.MM.UONSTR.HSTA",  # Euro Short-Term Rate
        "EONIA": "M.U2.EUR.4F.MM.EONIA.HSTA",    # Euro Overnight Index Average
    }
    
    rates = {}
    for name, series_key in reference_series.items():
        result = fetch_ecb_series("FM", series_key, last_n=1)
        if result and "value" in result:
            rates[name] = result["value"]
            logger.info(f"  {name}: {result['value']}%")
        else:
            logger.warning(f"  Could not fetch {name}")
    
    if rates:
        ref_data = {
            "fetch_date": datetime.now().isoformat(),
            "rates": rates,
            "source": "ECB Data Portal API (FM dataflow)",
        }
        save_to_json(ref_data, "ecb_reference_rates", CUSTOM_DATA_DIR)
        logger.info(f"  Saved reference rates ({len(rates)} rates)")
    else:
        logger.warning("  No reference rate data fetched. Skipping.")


def fetch_ecb_exchange_rates() -> None:
    """Fetch additional exchange rates from ECB."""
    logger.info("Fetching ECB exchange rates...")
    
    # Series keys for exchange rates (EUR base)
    # Format: EXR.D.{CURRENCY}.EUR.SP00.A
    exchange_series = {
        "EUR_USD": "D.USD.EUR.SP00.A",
        "EUR_GBP": "D.GBP.EUR.SP00.A",
        "EUR_JPY": "D.JPY.EUR.SP00.A",
        "EUR_CHF": "D.CHF.EUR.SP00.A",
    }
    
    rates = {}
    for name, series_key in exchange_series.items():
        result = fetch_ecb_series("EXR", series_key, last_n=1)
        if result and "value" in result:
            rates[name] = result["value"]
            logger.info(f"  {name}: {result['value']}")
        else:
            logger.warning(f"  Could not fetch {name}")
    
    if rates:
        fx_data = {
            "fetch_date": datetime.now().isoformat(),
            "rates": rates,
            "source": "ECB Data Portal API (EXR dataflow)",
        }
        save_to_json(fx_data, "ecb_exchange_rates", CUSTOM_DATA_DIR)
        logger.info(f"  Saved ECB exchange rates ({len(rates)} pairs)")
    else:
        logger.warning("  No exchange rate data fetched. Skipping.")


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


def fetch_supply_chain() -> None:
    """Fetch supply chain pressure index from NY Fed."""
    logger.info("Fetching NY Fed Supply Chain Pressure Index...")
    try:
        response = requests.get(NY_FED_SCP_URL, timeout=30)
        response.raise_for_status()
        
        # Parse CSV data
        import pandas as pd
        from io import StringIO
        
        df = pd.read_csv(StringIO(response.text))
        if df.empty:
            logger.warning("  No data returned")
            return
        
        # Convert to JSON-serializable format
        data = {
            "fetch_date": datetime.now().isoformat(),
            "latest_index": float(df.iloc[-1, 1]) if len(df.columns) > 1 else 0,
            "previous_index": float(df.iloc[-2, 1]) if len(df) > 1 and len(df.columns) > 1 else 0,
            "change": "N/A",
            "source": "Federal Reserve Bank of New York",
            "raw_data": df.to_dict(orient="records"),
        }
        
        save_to_json(data, "supply_chain", CUSTOM_DATA_DIR)
        logger.info("  Saved Supply Chain Pressure Index data")
    except Exception as e:
        logger.error(f"  Error fetching Supply Chain data: {e}")
        # Save mock data on error
        mock_data = {
            "fetch_date": datetime.now().isoformat(),
            "latest_index": 2.5,
            "previous_index": 2.3,
            "change": "+0.2",
            "source": "Federal Reserve Bank of New York",
            "note": "Mock data - actual API fetch failed",
        }
        save_to_json(mock_data, "supply_chain", CUSTOM_DATA_DIR)
        logger.info("  Saved mock Supply Chain data")


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


def fetch_all() -> None:
    """Fetch all custom data."""
    logger.info("=" * 60)
    logger.info("Starting Custom API data fetch")
    logger.info("=" * 60)
    
    # ECB Data Portal API fetches
    fetch_euribor()
    fetch_ecb_yield_curve()
    fetch_ecb_reference_rates()
    fetch_ecb_exchange_rates()
    
    # Other custom APIs
    fetch_gdelt()
    fetch_supply_chain()
    fetch_ipos()
    
    logger.info("=" * 60)
    logger.info("Custom API data fetch completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    fetch_all()
