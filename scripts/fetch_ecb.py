#!/usr/bin/env python3
"""Fetch ECB (European Central Bank) data from Data Portal API."""

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

logger = setup_logging("fetch_ecb")

# Configuration
CUSTOM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ECB Data Portal API configuration
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# Load API keys
FRED_KEY = get_api_key("FRED")
if FRED_KEY:
    os.environ["FRED_API_KEY"] = FRED_KEY

ECB_KEY = get_api_key("ECB")
if ECB_KEY:
    os.environ["ECB_API_KEY"] = ECB_KEY
    logger.info(f"ECB API key configured")


def fetch_ecb_series(
    dataflow: str,
    series_key: str,
    start_date: Optional[str] = None,
    timeout: int = 30
) -> Optional[dict]:
    """
    Fetch a single series from ECB Data Portal API.
    
    Args:
        dataflow: Dataflow ID (e.g., 'YC', 'EXR', 'FM')
        series_key: Series key within the dataflow
        start_date: Start date in YYYY-MM format (e.g., '2025-01'). If None, fetches last few observations.
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with latest value, observations history with dates, or None if error
    """
    url = f"{ECB_API_BASE}/{dataflow}/{series_key}"
    
    # Use CSV format to get actual dates in the TIME_PERIOD column
    from datetime import datetime
    
    if start_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
        params = {
            "format": "csvdata",
            "startPeriod": start_date,
            "endPeriod": end_date,
        }
    else:
        # Fetch enough observations to cover ~6 months
        params = {
            "format": "csvdata",
            "lastNObservations": "180",
        }
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code != 200:
            logger.warning(f"  ECB API returned {response.status_code} for {dataflow}/{series_key}")
            return None
        
        # Parse CSV response
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(response.text))
        parsed_obs = []
        
        for row in reader:
            try:
                time_period = row.get("TIME_PERIOD", "")
                obs_value = row.get("OBS_VALUE", "")
                
                if obs_value and obs_value.replace(".", "").replace("-", "").replace("e", "").replace("E", "") and time_period:
                    value = float(obs_value)
                    parsed_obs.append({
                        "time": time_period,
                        "value": value
                    })
            except (ValueError, TypeError):
                continue
        
        if not parsed_obs:
            return None
        
        # Sort by time (most recent last)
        parsed_obs.sort(key=lambda x: x["time"])
        
        latest = parsed_obs[-1]
        
        return {
            "value": latest["value"],
            "time": latest["time"],
            "observations": parsed_obs,  # Full history with actual dates
            "raw_data": response.text,
        }
        
    except Exception as e:
        logger.warning(f"  Error fetching {dataflow}/{series_key}: {e}")
        return None


def fetch_euribor() -> None:
    """Fetch Euribor rates from ECB Data Portal API.
    
    Uses the ECB's Data Portal API which requires no API key.
    The ECB publishes daily Euribor rates via SDMX-ML web service.
    API docs: https://data.ecb.europa.eu/help/api/data
    """
    logger.info("Fetching Euribor rates from ECB Data Portal...")
    
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
    series_history = {}
    
    for tenor, series_key in euribor_series.items():
        # Use lastNObservations to get daily data (180 = ~6 months of business days)
        result = fetch_ecb_series("FM", series_key, start_date=None)
        if result and "value" in result:
            rates[tenor] = result["value"]
            series_history[tenor] = result.get("observations", [])
            logger.info(f"  {tenor}: {result['value']}")
        else:
            logger.warning(f"  Could not fetch {tenor}")
    
    if rates:
        euribor_data = {
            "fetch_date": datetime.now().isoformat(),
            "rates": rates,
            "history": series_history,
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
            "history": {},
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
        "1Y": "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_1Y",
        "10Y": "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y",
    }
    
    yields = {}
    series_history = {}
    
    for maturity, series_key in yield_series.items():
        # Use lastNObservations to get daily data
        result = fetch_ecb_series("YC", series_key, start_date=None)
        if result and "value" in result:
            yields[maturity] = result["value"]
            series_history[maturity] = result.get("observations", [])
            logger.info(f"  {maturity}: {result['value']}%")
        else:
            logger.warning(f"  Could not fetch {maturity} yield")
    
    if yields:
        yield_data = {
            "fetch_date": datetime.now().isoformat(),
            "yields": yields,
            "history": series_history,
            "source": "ECB Data Portal API (YC dataflow)",
        }
        save_to_json(yield_data, "ecb_yield_curve", CUSTOM_DATA_DIR)
        logger.info(f"  Saved yield curve data ({len(yields)} maturities)")
    else:
        logger.warning("  No yield curve data fetched. Skipping.")


def fetch_ecb_reference_rates() -> None:
    """Fetch ECB reference rates (€STR) from ECB.
    
    Note: EONIA has been replaced by €STR (Euro Short-Term Rate) as the primary
    benchmark for euro-denominated overnight unsecured lending.
    """
    logger.info("Fetching ECB reference rates...")
    
    # Series keys for reference rates
    # €STR (Euro Short-Term Rate) - the modern ECB benchmark
    reference_series = {
        "ESTR": "M.U2.EUR.4F.MM.UONSTR.HSTA",  # Euro Short-Term Rate
    }
    
    rates = {}
    series_history = {}
    
    for name, series_key in reference_series.items():
        # Use lastNObservations to get daily data
        result = fetch_ecb_series("FM", series_key, start_date=None)
        if result and "value" in result:
            rates[name] = result["value"]
            series_history[name] = result.get("observations", [])
            logger.info(f"  {name}: {result['value']}%")
        else:
            logger.warning(f"  Could not fetch {name}")
    
    if rates:
        ref_data = {
            "fetch_date": datetime.now().isoformat(),
            "rates": rates,
            "history": series_history,
            "source": "ECB Data Portal API (FM dataflow)",
            "note": "EONIA has been replaced by €STR as the primary ECB benchmark rate",
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
        # Exchange rates - only need latest value, no history needed
        result = fetch_ecb_series("EXR", series_key)
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


def fetch_bond_spreads() -> None:
    """Fetch Spanish and German 10Y bond yields from FRED and calculate spread vs Bund."""
    logger.info("Fetching Spanish and German 10Y bond yields...")
    
    # Set FRED API key BEFORE importing obb
    FRED_KEY = get_api_key("FRED")
    if FRED_KEY:
        os.environ["FRED_API_KEY"] = FRED_KEY
    else:
        logger.warning("  FRED API key not found. Using mock data for bond spreads.")
        spread_data = {
            "fetch_date": datetime.now().isoformat(),
            "spain_10y": 3.45,
            "germany_10y": 3.00,
            "spread": 0.45,
            "history": {},
            "source": "Mock data (FRED API key not available)",
        }
        save_to_json(spread_data, "bond_spreads", CUSTOM_DATA_DIR)
        logger.info(f"  Saved bond spreads data (mock)")
        return
    
    try:
        from openbb import obb
        import pandas as pd
        
        # FRED series for 10Y government bond yields
        # Source: https://fred.stlouisfed.org/
        spain_series = "IRLTLT01ESM156N"  # Spain 10-Year Government Bond Yield
        germany_series = "IRLTLT01DEM156N"  # Germany 10-Year Government Bond Yield
        
        # Fetch data from FRED (5 years of history)
        start_date = "2020-01-01"
        
        spain_df = obb.economy.fred_series(symbol=spain_series, start_date=start_date).to_df()
        germany_df = obb.economy.fred_series(symbol=germany_series, start_date=start_date).to_df()
        
        if not spain_df.empty and not germany_df.empty:
            # Get latest values
            spain_yield = float(spain_df[spain_series].iloc[-1])
            germany_yield = float(germany_df[germany_series].iloc[-1])
            
            # Calculate spread as percentage
            spread = spain_yield - germany_yield
            
            # Prepare history for previous value calculation
            # Merge the two series on date and calculate spread history
            spain_df = spain_df.reset_index()
            spain_df.columns = ["date", "spain_10y"]
            germany_df = germany_df.reset_index()
            germany_df.columns = ["date", "germany_10y"]
            
            # Ensure date columns are datetime
            spain_df["date"] = pd.to_datetime(spain_df["date"])
            germany_df["date"] = pd.to_datetime(germany_df["date"])
            
            merged = pd.merge(spain_df, germany_df, on="date", how="inner")
            merged["spread"] = merged["spain_10y"] - merged["germany_10y"]
            
            # Convert dates to strings for JSON serialization
            merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
            spain_df["date"] = spain_df["date"].dt.strftime("%Y-%m-%d")
            germany_df["date"] = germany_df["date"].dt.strftime("%Y-%m-%d")
            
            # Get observations for each series
            spain_obs = [{"time": row["date"], "value": row["spain_10y"]} for _, row in spain_df.iterrows()]
            germany_obs = [{"time": row["date"], "value": row["germany_10y"]} for _, row in germany_df.iterrows()]
            spread_obs = [{"time": row["date"], "value": row["spread"]} for _, row in merged.iterrows()]
            
            spread_data = {
                "fetch_date": datetime.now().isoformat(),
                "spain_10y": spain_yield,
                "germany_10y": germany_yield,
                "spread": spread,
                "history": {
                    "spain_10y": spain_obs,
                    "germany_10y": germany_obs,
                    "spread": spread_obs,
                },
                "source": "FRED (Federal Reserve Economic Data)",
            }
            save_to_json(spread_data, "bond_spreads", CUSTOM_DATA_DIR)
            logger.info(f"  Spain 10Y: {spain_yield:.2f}%, Germany 10Y: {germany_yield:.2f}%, Spread: {spread:.2f}%")
        else:
            logger.warning("  Empty data received from FRED for bond spreads")
    except ImportError:
        logger.warning("  pandas not available. Using mock data for bond spreads.")
        spread_data = {
            "fetch_date": datetime.now().isoformat(),
            "spain_10y": 3.45,
            "germany_10y": 3.00,
            "spread": 0.45,
            "history": {},
            "source": "Mock data",
        }
        save_to_json(spread_data, "bond_spreads", CUSTOM_DATA_DIR)
    except Exception as e:
        logger.warning(f"  Could not fetch bond spread data: {e}. Using mock data.")
        spread_data = {
            "fetch_date": datetime.now().isoformat(),
            "spain_10y": 3.45,
            "germany_10y": 3.00,
            "spread": 0.45,
            "history": {},
            "source": "Mock data",
        }
        save_to_json(spread_data, "bond_spreads", CUSTOM_DATA_DIR)


if __name__ == "__main__":
    fetch_euribor()
    fetch_ecb_yield_curve()
    fetch_ecb_reference_rates()
    fetch_ecb_exchange_rates()
    fetch_bond_spreads()
