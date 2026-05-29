#!/usr/bin/env python3
"""Fetch Spanish real estate and mortgage indicators from INE."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.caching import (
    save_to_json,
    CUSTOM_DATA_DIR,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("fetch_spanish_real_estate")

# Configuration
CUSTOM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# INE (National Statistics Institute) API configuration
INE_API_BASE = "https://servicios.ine.es/wstempus/js/EN/DATOS_TABLA"

# Bank of Spain (Banco de España) API configuration
BDE_API_BASE = "https://app.bde.es/bierest/resources/srdatosapp"


def fetch_ine_series(
    table_id: str,
    series_code: str,
    nult: int = 10,
    timeout: int = 30
) -> Optional[dict]:
    """
    Fetch a series from INE (National Statistics Institute of Spain) API.
    
    Args:
        table_id: INE table ID (e.g., "25171" for House Price Index)
        series_code: Series code within the table (e.g., "IPV769")
        nult: Number of latest observations to fetch
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with latest value, previous value, and observations,
        or None if error
    """
    url = f"{INE_API_BASE}/{table_id}?nult={nult}"
    
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            logger.warning(f"  INE API returned {response.status_code} for table {table_id}")
            return None
        
        data = response.json()
        
        # Find the series with matching code
        target_series = None
        for series in data:
            if series.get("COD") == series_code:
                target_series = series
                break
        
        if not target_series:
            logger.warning(f"  Series {series_code} not found in table {table_id}")
            return None
        
        series_data = target_series.get("Data", [])
        
        if not series_data:
            logger.warning(f"  No data available for series {series_code}")
            return None
        
        # Sort by date (newest last)
        series_data.sort(key=lambda x: x.get("Fecha", 0))
        
        # Get latest and previous values
        latest = series_data[-1]
        previous = series_data[-2] if len(series_data) >= 2 else None
        
        latest_value = latest.get("Valor")
        previous_value = previous.get("Valor") if previous else None
        
        result = {
            "value": float(latest_value) if latest_value is not None else None,
            "previous": float(previous_value) if previous_value is not None else None,
            "date": datetime.fromtimestamp(latest.get("Fecha", 0) / 1000).isoformat() if latest.get("Fecha") else None,
        }
        
        return result
        
    except Exception as e:
        logger.warning(f"  Error fetching INE series {series_code} from table {table_id}: {e}")
        return None


def fetch_bde_series_with_history(
    series_code: str,
    time_range: str = "MAX",
    timeout: int = 30
) -> Optional[dict]:
    """
    Fetch a single series with full history from Bank of Spain API.
    
    Args:
        series_code: Series code to fetch
        time_range: Time range parameter (e.g., "30M", "MAX")
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with series data including history
    """
    url = f"{BDE_API_BASE}/listaSeries?idioma=en&series={series_code}&rango={time_range}"
    
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            logger.warning(f"  BDE API returned {response.status_code} for series {series_code}")
            return None
        
        data = response.json()
        
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"  No data returned for series {series_code}")
            return None
        
        series_data = data[0]
        
        dates = series_data.get("fechas", [])
        values = series_data.get("valores", [])
        
        if not dates or not values or len(dates) != len(values):
            logger.warning(f"  Mismatched dates/values for series {series_code}")
            return None
        
        # Parse dates and values
        observations = []
        for date_str, value in zip(dates, values):
            try:
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                observations.append({
                    "date": date_obj.isoformat(),
                    "value": float(value) if value is not None else None
                })
            except (ValueError, TypeError):
                continue
        
        if not observations:
            return None
        
        observations.sort(key=lambda x: x["date"])
        
        return {
            "latest": observations[-1]["value"],
            "previous": observations[-2]["value"] if len(observations) >= 2 else None,
            "observations": observations,
        }
        
    except Exception as e:
        logger.warning(f"  Error fetching BDE series {series_code} with history: {e}")
        return None


def calculate_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Calculate percentage change between current and previous values."""
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def fetch_spanish_real_estate() -> None:
    """Fetch Spanish real estate and mortgage indicators from INE.
    
    Indicators:
    1. House Price Index (IPV) - INE (Table 25171)
    2. Average Mortgage Interest Rate - INE (Table 24460)
    3. New Mortgage Loans Count - INE (Table 3200)
    4. New Mortgage Loans Value - INE (Table 3200)
    5. Fixed vs Variable Rate Share - INE (Table 24456)
    6. Mortgage Average Term - INE (Table 24458)
    """
    logger.info("Fetching Spanish Real Estate data...")
    
    indicators = {}
    
    # ========================================================================
    # House Price Index (IPV) from INE Table 25171
    # ========================================================================
    logger.info("  Fetching House Price Index from INE...")
    
    hpi_index = fetch_ine_series("25171", "IPV769", nult=10)
    hpi_annual = fetch_ine_series("25171", "IPV948", nult=10)
    hpi_quarterly = fetch_ine_series("25171", "IPV949", nult=10)
    
    if hpi_index and hpi_index.get("value") is not None:
        val = hpi_index["value"]
        prev = hpi_index.get("previous")
        chg_1y = hpi_annual.get("value") if hpi_annual and hpi_annual.get("value") else calculate_change(val, prev)
        chg_1m = hpi_quarterly.get("value") if hpi_quarterly and hpi_quarterly.get("value") else calculate_change(val, prev)
        
        indicators["house_price_index"] = {
            "value": val, "previous": prev,
            "change_1m": chg_1m, "change_1y": chg_1y,
            "unit": "index",
            "description": "House Price Index (IPV) - residential property prices",
            "source": "INE (National Statistics Institute)",
            "frequency": "Quarterly"
        }
        logger.info(f"    HPI: {val} (1M: {chg_1m}%, 1Y: {chg_1y}%)")
    else:
        logger.warning("    Could not fetch HPI")
        indicators["house_price_index"] = {
            "value": None, "previous": None, "change_1m": None, "change_1y": None,
            "unit": "index",
            "description": "House Price Index (IPV)",
            "source": "INE", "frequency": "Quarterly",
            "note": "NA - API unavailable"
        }
    
    # ========================================================================
    # Average Mortgage Rate from INE Table 24460
    # ========================================================================
    logger.info("  Fetching mortgage interest rate...")
    
    mortgage_rate = fetch_ine_series("24460", "HPT64422", nult=10)
    
    if mortgage_rate and mortgage_rate.get("value") is not None:
        val = mortgage_rate["value"]
        prev = mortgage_rate.get("previous")
        chg_1m = calculate_change(val, prev)
        chg_1y = calculate_change(val, prev)
        
        indicators["avg_mortgage_rate"] = {
            "value": val, "previous": prev,
            "change_1m": chg_1m, "change_1y": chg_1y,
            "unit": "",  # Empty: format_percentage adds % sign
            "description": "Average interest rate for new mortgage loans in Spain",
            "source": "INE (National Statistics Institute)",
            "frequency": "Monthly"
        }
        logger.info(f"    Mortgage Rate: {val}%")
    else:
        logger.warning("    Could not fetch mortgage rate")
        indicators["avg_mortgage_rate"] = {
            "value": None, "previous": None, "change_1m": None, "change_1y": None,
            "unit": "",
            "description": "Average interest rate for new mortgage loans",
            "source": "INE / BDE", "frequency": "Monthly",
            "note": "NA - API unavailable"
        }
    
    # ========================================================================
    # New Mortgage Loans Count from INE Table 3200
    # ========================================================================
    logger.info("  Fetching mortgage loans count...")
    
    count_data = fetch_ine_series("3200", "HPT34618", nult=10)
    
    if count_data and count_data.get("value") is not None:
        val = count_data["value"]
        prev = count_data.get("previous")
        chg_1m = calculate_change(val, prev)
        chg_1y = calculate_change(val, prev)
        
        indicators["new_mortgage_loans_count"] = {
            "value": int(val) if val else None,
            "previous": int(prev) if prev else None,
            "change_1m": chg_1m, "change_1y": chg_1y,
            "unit": "loans",
            "description": "Number of new mortgage loans signed in Spain",
            "source": "INE (National Statistics Institute)",
            "frequency": "Monthly"
        }
        logger.info(f"    Count: {int(val) if val else None}")
    else:
        logger.warning("    Could not fetch count")
        indicators["new_mortgage_loans_count"] = {
            "value": None, "previous": None, "change_1m": None, "change_1y": None,
            "unit": "loans",
            "description": "Number of new mortgage loans signed in Spain",
            "source": "INE", "frequency": "Monthly",
            "note": "NA"
        }
    
    # ========================================================================
    # New Mortgage Loans Value from INE Table 3200
    # ========================================================================
    logger.info("  Fetching mortgage loans value...")
    
    value_data = fetch_ine_series("3200", "HPT34565", nult=10)
    
    if value_data and value_data.get("value") is not None:
        val = value_data["value"]
        prev = value_data.get("previous")
        # Convert from thousands of euros to actual euros
        val_eur = int(val) * 1000 if val else None
        prev_eur = int(prev) * 1000 if prev else None
        chg_1m = calculate_change(val_eur, prev_eur) if val_eur and prev_eur else None
        chg_1y = calculate_change(val_eur, prev_eur) if val_eur and prev_eur else None
        
        indicators["new_mortgage_loans_value"] = {
            "value": val_eur,
            "previous": prev_eur,
            "change_1m": chg_1m, "change_1y": chg_1y,
            "unit": "€",
            "description": "Total value of new mortgage loans",
            "source": "INE (National Statistics Institute)",
            "frequency": "Monthly"
        }
        logger.info(f"    Value: {val_eur} €")
    else:
        logger.warning("    Could not fetch value")
        indicators["new_mortgage_loans_value"] = {
            "value": None, "previous": None, "change_1m": None, "change_1y": None,
            "unit": "€",
            "description": "Total value of new mortgage loans",
            "source": "INE", "frequency": "Monthly",
            "note": "NA"
        }
    
    # ========================================================================
    # Fixed vs Variable Rate Share from INE Table 24456
    # ========================================================================
    logger.info("  Fetching fixed vs variable rate share...")
    
    fixed_data = fetch_ine_series("24456", "HPT64401", nult=10)
    variable_data = fetch_ine_series("24456", "HPT64400", nult=10)
    
    if fixed_data and variable_data:
        fixed_val = fixed_data.get("value")
        variable_val = variable_data.get("value")
        
        if fixed_val is not None and variable_val is not None:
            total = fixed_val + variable_val
            if total > 0:
                fixed_pct = (fixed_val / total) * 100
                indicators["fixed_vs_variable_rate_share"] = {
                    "value": round(fixed_pct, 2), "previous": None,
                    "change_1m": None, "change_1y": None,
                    "unit": "",  # Empty: format_percentage adds % sign
                    "description": "Percentage of new mortgages with fixed interest rates",
                    "source": "INE (National Statistics Institute)",
                    "frequency": "Monthly"
                }
                logger.info(f"    Fixed Rate Share: {fixed_pct:.2f}%")
            else:
                indicators["fixed_vs_variable_rate_share"] = {
                    "value": None, "previous": None, "change_1m": None, "change_1y": None,
                    "unit": "",
                    "description": "Percentage of new mortgages with fixed interest rates",
                    "source": "INE", "frequency": "Monthly",
                    "note": "NA - Zero total"
                }
        else:
            indicators["fixed_vs_variable_rate_share"] = {
                "value": None, "previous": None, "change_1m": None, "change_1y": None,
                "unit": "",
                "description": "Percentage of new mortgages with fixed interest rates",
                "source": "INE", "frequency": "Monthly",
                "note": "NA - Missing data"
            }
    else:
        logger.warning("    Could not fetch fixed/variable data")
        indicators["fixed_vs_variable_rate_share"] = {
            "value": None, "previous": None, "change_1m": None, "change_1y": None,
            "unit": "",
            "description": "Percentage of new mortgages with fixed interest rates",
            "source": "INE", "frequency": "Monthly",
            "note": "NA - API unavailable"
        }
    
    # ========================================================================
    # Mortgage Average Term from INE Table 24458
    # ========================================================================
    logger.info("  Fetching mortgage average term...")
    
    term_data = fetch_ine_series("24458", "HPT64412", nult=10)
    
    if term_data and term_data.get("value") is not None:
        val = term_data["value"]
        prev = term_data.get("previous")
        chg_1m = calculate_change(val, prev)
        chg_1y = calculate_change(val, prev)
        
        indicators["mortgage_approval_time"] = {
            "value": round(val, 1) if val else None,
            "previous": round(prev, 1) if prev else None,
            "change_1m": chg_1m, "change_1y": chg_1y,
            "unit": "years",
            "description": "Average term of new mortgage loans in Spain",
            "source": "INE (National Statistics Institute)",
            "frequency": "Monthly"
        }
        logger.info(f"    Average Term: {val} years")
    else:
        logger.warning("    Could not fetch term")
        indicators["mortgage_approval_time"] = {
            "value": None, "previous": None, "change_1m": None, "change_1y": None,
            "unit": "years",
            "description": "Average mortgage term",
            "source": "INE", "frequency": "Monthly",
            "note": "NA - API unavailable"
        }
    
    # Build final data structure
    real_estate_data = {
        "fetch_date": datetime.now().isoformat(),
        "indicators": indicators,
        "source": "INE (National Statistics Institute of Spain)",
        "note": "All 6 indicators use real API data from INE: House Price Index, Average Mortgage Rate, New Mortgage Loans (Count & Value), Fixed vs Variable Rate Share, and Mortgage Average Term."
    }
    
    save_to_json(real_estate_data, "spanish_real_estate", CUSTOM_DATA_DIR)
    logger.info("  Saved Spanish Real Estate data")


if __name__ == "__main__":
    fetch_spanish_real_estate()
