#!/usr/bin/env python3
"""
Generate macroeconomic financial report from cached data.

This script loads data from the cache and generates a PDF/HTML report
with executive summary, market snapshot, macroeconomic dashboard, and visualizations.
"""

import argparse
import base64
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.caching import (
    load_from_csv,
    load_from_json,
    CUSTOM_DATA_DIR,
)
from scripts.utils.formatting import (
    format_number,
    format_percentage,
    format_date,
    get_traffic_light_signal,
    get_traffic_light_signal_higher_better,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("generate_report")

# Configuration
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Directory published to GitHub Pages (the site root).
PAGES_DIR = Path(__file__).parent.parent / "docs"


def image_to_data_uri(image_path: str | Path) -> str:
    """Embed an image as a base64 data URI.

    Embedding charts inline keeps the HTML report self-contained, so it renders
    correctly when published to GitHub Pages without serving the PNG files.
    """
    path = Path(image_path)
    if not path.exists():
        return ""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"

# Traffic light thresholds
THRESHOLDS: dict[str, dict[str, int | float]] = {
    "vix": {"red": 20, "yellow": 15},
    "sp500_change": {"red": -5, "yellow": -2, "green": 2},  # Negative thresholds
    "gold_change": {"red": -5, "yellow": -2},
    "usd_eur": {"red": 1.15, "yellow": 1.10},  # EUR/USD rate
    "cpi": {"red": 4.0, "yellow": 2.5},  # Inflation rate
    "unemployment": {"red": 6.0, "yellow": 4.5},  # Unemployment rate
    "treasury_10y": {"red": 5.0, "yellow": 4.0},  # 10Y Treasury yield
    "euribor_12m_estr_spread": {"red": 1.0, "yellow": 0.5},  # Euribor 12M - ECB €STR spread (>100bps=red, 50-100bps=yellow)
    "euribor_12m": {"red": 5.0, "yellow": 3.5},  # Euribor 12M rate
    "spain_germany_10y_spread": {"red": 2.0, "yellow": 1.0},  # Spain-Germany 10Y spread (>2%=red, 1-2%=yellow)
    "gdp_growth": {"red": -1.0, "yellow": 1.5},  # GDP growth rate
    "gdp_yoy": {"red": -1.0, "yellow": 1.5},  # YoY GDP growth rate
    "ecb_yield": {"red": 5.0, "yellow": 3.5},  # ECB bond yields
    "ecb_rates": {"red": 3.0, "yellow": 2.0},  # ECB policy/reference rates
}


def get_latest_value(df: pd.DataFrame, column: str = "close") -> float:
    """Get the latest value from a DataFrame."""
    if df.empty:
        return 0.0
    # Sort by date if it exists
    if "date" in df.columns:
        df = df.sort_values("date")
    elif "DATE" in df.columns:
        df = df.sort_values("DATE")
    
    if column in df.columns:
        return float(df[column].iloc[-1])
    # For CPI-like data, value might be in a 'value' column
    if "value" in df.columns:
        return float(df["value"].iloc[-1])
    # Try common value column names
    for col in ["close", "GDP", "GDPC1", "value", "rate"]:
        if col in df.columns:
            try:
                return float(df[col].iloc[-1])
            except (ValueError, TypeError):
                continue
    # Fallback to last numeric column
    for col in reversed(df.columns):
        if col.lower() not in ("date", "DATE", "symbol", "time"):
            try:
                return float(df[col].iloc[-1])
            except (ValueError, TypeError):
                continue
    return 0.0


def get_previous_value(df: pd.DataFrame, column: str = "close", days: int = 30) -> float:
    """Get the value from n days ago."""
    if df.empty:
        return 0.0
    # Sort by date if it exists
    if "date" in df.columns:
        df = df.sort_values("date")
    elif "DATE" in df.columns:
        df = df.sort_values("DATE")
    
    # Find the right column
    target_col = None
    if column in df.columns:
        target_col = column
    elif "value" in df.columns:
        target_col = "value"
    else:
        for col in ["close", "GDP", "GDPC1", "value", "rate"]:
            if col in df.columns:
                target_col = col
                break
        if not target_col:
            for col in reversed(df.columns):
                if col.lower() not in ("date", "DATE", "symbol", "time"):
                    target_col = col
                    break
    
    if target_col:
        if len(df) >= days + 1:
            try:
                return float(df[target_col].iloc[-days - 1])
            except (ValueError, TypeError):
                return 0.0
        try:
            return float(df[target_col].iloc[0])
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def calculate_change(df: pd.DataFrame, column: str = "close", days: int = 30) -> float:
    """Calculate percentage change over n days."""
    latest = get_latest_value(df, column)
    previous = get_previous_value(df, column, days)
    if previous == 0:
        return 0.0
    return (latest - previous) / abs(previous) * 100


def get_previous_month_value(obs_list: list) -> float:
    """
    Get the value from approximately one month ago from a list of dated observations.
    Observations should have 'time' (date string) and 'value' keys, sorted oldest first.
    """
    if not obs_list or len(obs_list) < 2:
        return 0.0
    
    # Get the latest date
    latest_obs = obs_list[-1]
    try:
        from datetime import datetime
        # Try to parse the latest date
        try:
            latest_date = datetime.strptime(latest_obs["time"], "%Y-%m")
        except ValueError:
            try:
                latest_date = datetime.strptime(latest_obs["time"], "%Y-%m-%d")
            except ValueError:
                # Relative index - use second to last
                return obs_list[-2]["value"] if len(obs_list) >= 2 else 0.0
        
        # Find observation from ~30 days ago
        target_date = latest_date - timedelta(days=30)
        
        # Find the observation closest to but before the target date
        best_obs = None
        for obs in reversed(obs_list[:-1]):  # Exclude the latest, check oldest to newest
            try:
                obs_date = datetime.strptime(obs["time"], "%Y-%m")
            except ValueError:
                try:
                    obs_date = datetime.strptime(obs["time"], "%Y-%m-%d")
                except ValueError:
                    continue
            
            if obs_date <= target_date:
                best_obs = obs
                break
        
        if best_obs:
            return best_obs["value"]
        else:
            # Fallback to second observation from end
            return obs_list[-2]["value"] if len(obs_list) >= 2 else 0.0
    except Exception:
        return obs_list[-2]["value"] if len(obs_list) >= 2 else 0.0


def get_previous_year_value(obs_list: list) -> float:
    """
    Get the value from approximately one year ago from a list of dated observations.
    Observations should have 'time' (date string) and 'value' keys, sorted oldest first.
    """
    if not obs_list or len(obs_list) < 2:
        return 0.0

    # Get the latest date
    latest_obs = obs_list[-1]
    try:
        from datetime import datetime
        # Try to parse the latest date
        try:
            latest_date = datetime.strptime(latest_obs["time"], "%Y-%m")
        except ValueError:
            try:
                latest_date = datetime.strptime(latest_obs["time"], "%Y-%m-%d")
            except ValueError:
                # Relative index - use second to last if we don't have enough data
                return obs_list[-2]["value"] if len(obs_list) >= 2 else 0.0
        
        # Find observation from ~365 days ago
        target_date = latest_date - timedelta(days=365)
        
        # Find the observation closest to but before the target date
        best_obs = None
        for obs in reversed(obs_list[:-1]):  # Exclude the latest, check oldest to newest
            try:
                obs_date = datetime.strptime(obs["time"], "%Y-%m")
            except ValueError:
                try:
                    obs_date = datetime.strptime(obs["time"], "%Y-%m-%d")
                except ValueError:
                    continue
            
            if obs_date <= target_date:
                best_obs = obs
                break
        
        if best_obs:
            return best_obs["value"]
        else:
            # Fallback to second observation from end
            return obs_list[-2]["value"] if len(obs_list) >= 2 else 0.0
    except Exception:
        return obs_list[-2]["value"] if len(obs_list) >= 2 else 0.0


def create_market_snapshot() -> dict:
    """Create market snapshot data."""
    snapshot = {}
    
    # Market indices
    indices = ["sp500", "stoxx600", "msci_world", "vix"]
    for name in indices:
        try:
            df = load_from_csv(name)
            snapshot[name] = {
                "value": get_latest_value(df, "close"),
                "change_1m": calculate_change(df, "close", 30),
                "change_1y": calculate_change(df, "close", 365),
            }
        except Exception as e:
            logger.warning(f"Error loading {name.replace('_', ' ').title()}: {e}")
            snapshot[name] = {"value": 0, "change_1m": 0, "change_1y": 0}
    
    # Commodities
    commodities = ["gold", "brent_crude", "copper", "wheat"]
    for name in commodities:
        try:
            df = load_from_csv(name)
            snapshot[name] = {
                "value": get_latest_value(df, "close"),
                "change_1m": calculate_change(df, "close", 30),
                "change_1y": calculate_change(df, "close", 365),
            }
        except Exception as e:
            logger.warning(f"Error loading {name.replace('_', ' ').title()}: {e}")
            snapshot[name] = {"value": 0, "change_1m": 0, "change_1y": 0}
    
    # Forex
    forex = ["usd_eur", "usd_cny"]
    for name in forex:
        try:
            df = load_from_csv(name)
            snapshot[name] = {
                "value": get_latest_value(df, "close"),
                "change_1m": calculate_change(df, "close", 30),
                "change_1y": calculate_change(df, "close", 365),
            }
        except Exception as e:
            logger.warning(f"Error loading {name.upper()}: {e}")
            snapshot[name] = {"value": 0, "change_1m": 0, "change_1y": 0}
    
    return snapshot


def create_macro_dashboard() -> dict:
    """Create macroeconomic dashboard data."""
    dashboard = {}
    
    # CPI - Monthly data, use immediate previous month
    # Note: CPI data comes as decimals (0.04 = 4%), convert to percentages
    try:
        cpi = load_from_csv("us_cpi")
        latest = get_latest_value(cpi) * 100
        # For monthly data, previous = prior month (1 position back)
        previous = get_previous_value(cpi, days=1) * 100 if len(cpi) >= 2 else 0
        change = calculate_change(cpi, days=1) if len(cpi) >= 2 else 0
        change_1y = calculate_change(cpi, days=365) if len(cpi) >= 2 else 0
        dashboard["us_cpi"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading US CPI: {e}")
        dashboard["us_cpi"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # Unemployment - Monthly data, use immediate previous month
    # Note: Unemployment data comes as decimals (0.04 = 4%), convert to percentages
    try:
        unemployment = load_from_csv("us_unemployment")
        latest = get_latest_value(unemployment) * 100
        # For monthly data, previous = prior month (1 position back)
        previous = get_previous_value(unemployment, days=1) * 100 if len(unemployment) >= 2 else 0
        change = calculate_change(unemployment, days=1) if len(unemployment) >= 2 else 0
        change_1y = calculate_change(unemployment, days=365) if len(unemployment) >= 2 else 0
        dashboard["us_unemployment"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading US Unemployment: {e}")
        dashboard["us_unemployment"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # EU CPI - Monthly data
    try:
        eu_cpi = load_from_csv("eu_cpi")
        latest = get_latest_value(eu_cpi) * 100
        previous = get_previous_value(eu_cpi, days=1) * 100 if len(eu_cpi) >= 2 else 0
        change = calculate_change(eu_cpi, days=1) if len(eu_cpi) >= 2 else 0
        change_1y = calculate_change(eu_cpi, days=365) if len(eu_cpi) >= 2 else 0
        dashboard["eu_cpi"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading EU CPI: {e}")
        dashboard["eu_cpi"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # EU Unemployment - Monthly data
    try:
        eu_unemployment = load_from_csv("eu_unemployment")
        latest = get_latest_value(eu_unemployment) * 100
        previous = get_previous_value(eu_unemployment, days=1) * 100 if len(eu_unemployment) >= 2 else 0
        change = calculate_change(eu_unemployment, days=1) if len(eu_unemployment) >= 2 else 0
        change_1y = calculate_change(eu_unemployment, days=365) if len(eu_unemployment) >= 2 else 0
        dashboard["eu_unemployment"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading EU Unemployment: {e}")
        dashboard["eu_unemployment"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # Spain CPI - Monthly data
    try:
        spain_cpi = load_from_csv("spain_cpi")
        latest = get_latest_value(spain_cpi) * 100
        previous = get_previous_value(spain_cpi, days=1) * 100 if len(spain_cpi) >= 2 else 0
        change = calculate_change(spain_cpi, days=1) if len(spain_cpi) >= 2 else 0
        change_1y = calculate_change(spain_cpi, days=365) if len(spain_cpi) >= 2 else 0
        dashboard["spain_cpi"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading Spain CPI: {e}")
        dashboard["spain_cpi"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # Spain Unemployment - Monthly data
    try:
        spain_unemployment = load_from_csv("spain_unemployment")
        latest = get_latest_value(spain_unemployment) * 100
        previous = get_previous_value(spain_unemployment, days=1) * 100 if len(spain_unemployment) >= 2 else 0
        change = calculate_change(spain_unemployment, days=1) if len(spain_unemployment) >= 2 else 0
        change_1y = calculate_change(spain_unemployment, days=365) if len(spain_unemployment) >= 2 else 0
        dashboard["spain_unemployment"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading Spain Unemployment: {e}")
        dashboard["spain_unemployment"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # GDP (nominal) - Quarterly data, use immediate previous quarter
    try:
        gdp = load_from_csv("us_gdp")
        latest = get_latest_value(gdp)
        # For quarterly data, previous = prior quarter (1 position back)
        previous = get_previous_value(gdp, days=1) if len(gdp) >= 2 else 0
        change = calculate_change(gdp, days=1) if len(gdp) >= 2 else 0
        change_1y = calculate_change(gdp, days=365) if len(gdp) >= 2 else 0
        dashboard["us_gdp"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading US GDP: {e}")
        dashboard["us_gdp"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # GDP Real - Quarterly data, use immediate previous quarter
    try:
        gdp_real = load_from_csv("us_gdp_real")
        latest = get_latest_value(gdp_real)
        # For quarterly data, previous = prior quarter (1 position back)
        previous = get_previous_value(gdp_real, days=1) if len(gdp_real) >= 2 else 0
        change = calculate_change(gdp_real, days=1) if len(gdp_real) >= 2 else 0
        change_1y = calculate_change(gdp_real, days=365) if len(gdp_real) >= 2 else 0
        dashboard["us_gdp_real"] = {
            "value": latest,
            "previous": previous,
            "change_1m": change,
            "change_1y": change_1y,
        }
    except Exception as e:
        logger.warning(f"Error loading US GDP Real: {e}")
        dashboard["us_gdp_real"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # GDP YoY (Year-over-Year growth rate) - from country_profile
    gdp_yoy_countries = ["us_gdp_yoy", "eu_gdp_yoy", "spain_gdp_yoy"]
    for name in gdp_yoy_countries:
        try:
            gdp_data = load_from_csv(name)
            if not gdp_data.empty:
                # The CSV has a gdp_yoy column with the value
                latest = get_latest_value(gdp_data, "gdp_yoy") * 100  # Convert to percentage
                # For YoY data, we don't have history in the current format
                change_1y = calculate_change(gdp_data, "gdp_yoy", days=365) if len(gdp_data) >= 2 else 0
                dashboard[name] = {
                    "value": latest,
                    "previous": 0,
                    "change_1m": 0,
                    "change_1y": change_1y,
                }
            else:
                dashboard[name] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
        except Exception as e:
            logger.warning(f"Error loading {name}: {e}")
            dashboard[name] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # ECB Yield Curve (from custom data)
    try:
        yield_curve = load_from_json("ecb_yield_curve", CUSTOM_DATA_DIR)
        if "yields" in yield_curve and isinstance(yield_curve["yields"], dict):
            history = yield_curve.get("history", {})
            for maturity, value in yield_curve["yields"].items():
                prev_val = 0
                change_1m = 0
                # Get historical observations for this maturity
                obs_list = history.get(maturity, [])
                prev_1y_val = 0
                change_1y = 0
                if obs_list and len(obs_list) >= 2:
                    # Observations are sorted oldest first, newest last
                    # Use helper to find value from ~1 month ago
                    prev_val = get_previous_month_value(obs_list)
                    # Calculate change from previous month
                    if prev_val != 0:
                        change_1m = ((value - prev_val) / abs(prev_val)) * 100
                    # Use helper to find value from ~1 year ago
                    prev_1y_val = get_previous_year_value(obs_list)
                    if prev_1y_val != 0:
                        change_1y = ((value - prev_1y_val) / abs(prev_1y_val)) * 100
                dashboard[f"ecb_yield_{maturity.lower()}"] = {
                    "value": value,
                    "previous": prev_val,
                    "change_1m": change_1m,
                    "change_1y": change_1y,
                }
    except Exception as e:
        logger.warning(f"Error loading ECB yield curve: {e}")
    
    # ECB Reference Rates (from custom data) - Note: ESTR is loaded but not added to dashboard
    # as it's only used for the Euribor 12M - €STR spread calculation
    try:
        ref_rates = load_from_json("ecb_reference_rates", CUSTOM_DATA_DIR)
        if "rates" in ref_rates and isinstance(ref_rates["rates"], dict):
            history = ref_rates.get("history", {})
            for name, value in ref_rates["rates"].items():
                # Skip ESTR - it's only used for spread calculation, not displayed separately
                if name == "ESTR":
                    continue
                prev_val = 0
                change_1m = 0
                change_1y = 0
                # Get historical observations for this rate
                obs_list = history.get(name, [])
                if obs_list and len(obs_list) >= 2:
                    # Observations are sorted oldest first, newest last
                    # Use helper to find value from ~1 month ago
                    prev_val = get_previous_month_value(obs_list)
                    # Calculate change from previous month
                    if prev_val != 0:
                        change_1m = ((value - prev_val) / abs(prev_val)) * 100
                    # Use helper to find value from ~1 year ago
                    prev_1y_val = get_previous_year_value(obs_list)
                    if prev_1y_val != 0:
                        change_1y = ((value - prev_1y_val) / abs(prev_1y_val)) * 100
                dashboard[f"ecb_{name.lower()}"] = {
                    "value": value,
                    "previous": prev_val,
                    "change_1m": change_1m,
                    "change_1y": change_1y,
                }
    except Exception as e:
        logger.warning(f"Error loading ECB reference rates: {e}")
    
    # Treasury rates
    try:
        treasury = load_from_csv("us_treasury_rates")
        # Get 10Y rate - column might be year_10 or 10Y
        treasury_col = None
        for col in ["year_10", "10Y", "10year", "year10"]:
            if col in treasury.columns:
                treasury_col = col
                break
        
        if treasury_col:
            # Treasury rates are returned as decimals (e.g., 0.0445 = 4.45%)
            # Convert to percentage for display
            latest = get_latest_value(treasury, treasury_col) * 100
            previous = get_previous_value(treasury, treasury_col, 30) * 100
            change = calculate_change(treasury, treasury_col, 30)
            change_1y = calculate_change(treasury, treasury_col, 365)
            dashboard["treasury_10y"] = {
                "value": latest,
                "previous": previous,
                "change_1m": change,
                "change_1y": change_1y,
            }
        else:
            # Try to find any column with '10' in it
            for col in treasury.columns:
                if "10" in str(col).lower():
                    latest = get_latest_value(treasury, col) * 100
                    previous = get_previous_value(treasury, col, 30) * 100
                    change = calculate_change(treasury, col, 30)
                    change_1y = calculate_change(treasury, col, 365)
                    dashboard["treasury_10y"] = {
                        "value": latest,
                        "previous": previous,
                        "change_1m": change,
                        "change_1y": change_1y,
                    }
                    break
            else:
                dashboard["treasury_10y"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    except Exception as e:
        logger.warning(f"Error loading Treasury rates: {e}")
        dashboard["treasury_10y"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # Euribor 12M - ECB €STR spread (from custom data)
    try:
        euribor = load_from_json("euribor", CUSTOM_DATA_DIR)
        ref_rates = load_from_json("ecb_reference_rates", CUSTOM_DATA_DIR)
        
        euribor_12m = 0
        estr = 0
        
        # Get Euribor 12M rate
        if "rates" in euribor and isinstance(euribor["rates"], dict):
            if "EURIBOR_12M" in euribor["rates"]:
                euribor_12m = euribor["rates"]["EURIBOR_12M"]
            else:
                # Try to find any 12M rate
                for key, value in euribor["rates"].items():
                    if "12M" in key or "12MONTH" in key:
                        euribor_12m = value
                        break
        
        # Get ECB €STR rate
        if "rates" in ref_rates and isinstance(ref_rates["rates"], dict):
            if "ESTR" in ref_rates["rates"]:
                estr = ref_rates["rates"]["ESTR"]
            else:
                # Try to find any ESTR rate
                for key, value in ref_rates["rates"].items():
                    if "ESTR" in key or "STR" in key:
                        estr = value
                        break
        
        # Add Euribor 12M as a separate indicator
        if euribor_12m > 0:
            euribor_12m_prev = 0
            euribor_12m_change_1m = 0
            euribor_12m_change_1y = 0
            
            # Get Euribor 12M history for previous month calculation
            euribor_12m_obs = None
            if "EURIBOR_12M" in euribor.get("history", {}):
                euribor_12m_obs = euribor["history"]["EURIBOR_12M"]
            else:
                for key, obs_list in euribor.get("history", {}).items():
                    if "12M" in key or "12MONTH" in key:
                        euribor_12m_obs = obs_list
                        break
            
            # Calculate previous month value and change
            if euribor_12m_obs and len(euribor_12m_obs) >= 2:
                euribor_12m_prev = get_previous_month_value(euribor_12m_obs)
                if euribor_12m_prev > 0:
                    euribor_12m_change_1m = ((euribor_12m - euribor_12m_prev) / abs(euribor_12m_prev)) * 100
                # Calculate 1-year change
                euribor_12m_prev_1y = get_previous_year_value(euribor_12m_obs)
                if euribor_12m_prev_1y > 0:
                    euribor_12m_change_1y = ((euribor_12m - euribor_12m_prev_1y) / abs(euribor_12m_prev_1y)) * 100
            
            dashboard["euribor_12m"] = {
                "value": euribor_12m,
                "previous": euribor_12m_prev,
                "change_1m": euribor_12m_change_1m,
                "change_1y": euribor_12m_change_1y,
            }
        else:
            dashboard["euribor_12m"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
        
        # Calculate spread
        if euribor_12m > 0 and estr > 0:
            spread = euribor_12m - estr
            
            # Calculate previous month spread
            prev_spread = 0
            change_1m = 0
            
            # Get historical data for both
            euribor_history = euribor.get("history", {})
            ref_history = ref_rates.get("history", {})
            
            # Try to get previous month values
            euribor_12m_obs = None
            estr_obs = None
            
            # Find 12M Euribor history
            if "EURIBOR_12M" in euribor_history:
                euribor_12m_obs = euribor_history["EURIBOR_12M"]
            else:
                for key, obs_list in euribor_history.items():
                    if "12M" in key or "12MONTH" in key:
                        euribor_12m_obs = obs_list
                        break
            
            # Find ESTR history
            if "ESTR" in ref_history:
                estr_obs = ref_history["ESTR"]
            else:
                for key, obs_list in ref_history.items():
                    if "ESTR" in key or "STR" in key:
                        estr_obs = obs_list
                        break
            
            change_1y = 0
            # If we have history for both, calculate previous month spread and 1-year spread
            if euribor_12m_obs and estr_obs and len(euribor_12m_obs) >= 2 and len(estr_obs) >= 2:
                prev_euribor_12m = get_previous_month_value(euribor_12m_obs)
                prev_estr = get_previous_month_value(estr_obs)
                if prev_euribor_12m > 0 and prev_estr > 0:
                    prev_spread = prev_euribor_12m - prev_estr
                    if prev_spread != 0:
                        change_1m = ((spread - prev_spread) / abs(prev_spread)) * 100
                # Calculate 1-year spread change - only if we have sufficient history
                prev_euribor_12m_1y = get_previous_year_value(euribor_12m_obs)
                prev_estr_1y = get_previous_year_value(estr_obs)
                if prev_euribor_12m_1y > 0 and prev_estr_1y > 0:
                    prev_spread_1y = prev_euribor_12m_1y - prev_estr_1y
                    if prev_spread_1y != 0:
                        change_1y = ((spread - prev_spread_1y) / abs(prev_spread_1y)) * 100
            
            dashboard["euribor_12m_estr_spread"] = {
                "value": spread,
                "previous": prev_spread,
                "change_1m": change_1m,
                "change_1y": change_1y,
            }
        else:
            dashboard["euribor_12m_estr_spread"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    except Exception as e:
        logger.warning(f"Error loading Euribor spread: {e}")
        dashboard["euribor_12m_estr_spread"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    # Spanish-German 10Y bond spread (from custom data)
    try:
        bond_spreads = load_from_json("bond_spreads", CUSTOM_DATA_DIR)
        if "spread" in bond_spreads:
            spread = bond_spreads["spread"]
            history = bond_spreads.get("history", {})
            
            prev_spread = 0
            change_1m = 0
            change_1y = 0
            
            # Get spread history and calculate previous month value
            spread_obs = history.get("spread", [])
            if spread_obs and len(spread_obs) >= 2:
                prev_spread = get_previous_month_value(spread_obs)
                if prev_spread != 0:
                    change_1m = ((spread - prev_spread) / abs(prev_spread)) * 100
                # Calculate 1-year change
                prev_spread_1y = get_previous_year_value(spread_obs)
                if prev_spread_1y != 0:
                    change_1y = ((spread - prev_spread_1y) / abs(prev_spread_1y)) * 100
            
            dashboard["spain_germany_10y_spread"] = {
                "value": spread,
                "previous": prev_spread,
                "change_1m": change_1m,
                "change_1y": change_1y,
            }
        else:
            dashboard["spain_germany_10y_spread"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    except Exception as e:
        logger.warning(f"Error loading bond spreads: {e}")
        dashboard["spain_germany_10y_spread"] = {"value": 0, "previous": 0, "change_1m": 0, "change_1y": 0}
    
    return dashboard


def create_visualizations(snapshot: dict, dashboard: dict) -> list:
    """Create matplotlib visualizations and save as images."""
    visualizations = []
    
    # Gruvbox Dark color palette
    GRUVBOX_BG = "#282828"
    GRUVBOX_FG = "#ebdbb2"
    GRUVBOX_GRAY = "#504945"
    GRUVBOX_RED = "#fb4934"
    GRUVBOX_GREEN = "#b8bb26"
    GRUVBOX_YELLOW = "#fabd2f"
    GRUVBOX_BLUE = "#83a598"
    GRUVBOX_PURPLE = "#d3869b"
    
    # Create sp500 trend chart (365 days)
    try:
        sp500 = load_from_csv("sp500")
        # Convert date strings to datetime for proper plotting
        sp500["date"] = pd.to_datetime(sp500["date"])
        # Filter to last 365 days
        cutoff = datetime.now() - timedelta(days=365)
        sp500 = sp500[sp500["date"] >= cutoff]
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Gruvbox styling
        fig.patch.set_facecolor(GRUVBOX_BG)
        ax.set_facecolor(GRUVBOX_BG)
        ax.plot(sp500["date"], sp500["close"], label="S&P 500", color=GRUVBOX_BLUE, linewidth=2)
        ax.set_title("S&P 500 Price Trend (1 Year)", color=GRUVBOX_FG)
        ax.set_xlabel("Date", color=GRUVBOX_FG)
        ax.set_ylabel("Price", color=GRUVBOX_FG)
        ax.legend(facecolor=GRUVBOX_BG, labelcolor=GRUVBOX_FG)
        ax.grid(True, color=GRUVBOX_GRAY, alpha=0.3)
        ax.tick_params(colors=GRUVBOX_FG)
        ax.spines['bottom'].set_color(GRUVBOX_FG)
        ax.spines['top'].set_color(GRUVBOX_FG)
        ax.spines['left'].set_color(GRUVBOX_FG)
        ax.spines['right'].set_color(GRUVBOX_FG)
        
        # Show one label per month
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.tight_layout()
        
        img_path = REPORTS_DIR / "sp500_trend.png"
        fig.savefig(img_path, dpi=300, bbox_inches="tight", facecolor=GRUVBOX_BG)
        plt.close(fig)
        visualizations.append({"title": "S&P 500 Trend", "path": str(img_path)})
        logger.info("  Created S&P 500 trend chart")
    except Exception as e:
        logger.error(f"  Error creating S&P 500 chart: {e}")
    
    # Create STOXX 600 trend chart (365 days)
    try:
        stoxx600 = load_from_csv("stoxx600")
        # Convert date strings to datetime for proper plotting
        stoxx600["date"] = pd.to_datetime(stoxx600["date"])
        # Filter to last 365 days
        cutoff = datetime.now() - timedelta(days=365)
        stoxx600 = stoxx600[stoxx600["date"] >= cutoff]
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Gruvbox styling
        fig.patch.set_facecolor(GRUVBOX_BG)
        ax.set_facecolor(GRUVBOX_BG)
        ax.plot(stoxx600["date"], stoxx600["close"], label="STOXX 600", color=GRUVBOX_GREEN, linewidth=2)
        ax.set_title("STOXX 600 Price Trend (1 Year)", color=GRUVBOX_FG)
        ax.set_xlabel("Date", color=GRUVBOX_FG)
        ax.set_ylabel("Price", color=GRUVBOX_FG)
        ax.legend(facecolor=GRUVBOX_BG, labelcolor=GRUVBOX_FG)
        ax.grid(True, color=GRUVBOX_GRAY, alpha=0.3)
        ax.tick_params(colors=GRUVBOX_FG)
        ax.spines['bottom'].set_color(GRUVBOX_FG)
        ax.spines['top'].set_color(GRUVBOX_FG)
        ax.spines['left'].set_color(GRUVBOX_FG)
        ax.spines['right'].set_color(GRUVBOX_FG)
        
        # Show one label per month
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.tight_layout()
        
        img_path = REPORTS_DIR / "stoxx600_trend.png"
        fig.savefig(img_path, dpi=300, bbox_inches="tight", facecolor=GRUVBOX_BG)
        plt.close(fig)
        visualizations.append({"title": "STOXX 600 Trend", "path": str(img_path)})
        logger.info("  Created STOXX 600 trend chart")
    except Exception as e:
        logger.error(f"  Error creating STOXX 600 chart: {e}")
    
    # Create VIX vs Gold chart (365 days)
    try:
        vix = load_from_csv("vix")
        gold = load_from_csv("gold")
        # Convert date strings to datetime for proper plotting
        vix["date"] = pd.to_datetime(vix["date"])
        gold["date"] = pd.to_datetime(gold["date"])
        # Filter to last 365 days
        cutoff = datetime.now() - timedelta(days=365)
        vix = vix[vix["date"] >= cutoff]
        gold = gold[gold["date"] >= cutoff]
        
        fig, ax1 = plt.subplots(figsize=(10, 4))
        
        # Gruvbox styling
        fig.patch.set_facecolor(GRUVBOX_BG)
        ax1.set_facecolor(GRUVBOX_BG)
        
        # VIX on left axis - use red for volatility
        ax1.set_xlabel("Date", color=GRUVBOX_FG)
        ax1.set_ylabel("VIX", color=GRUVBOX_RED)
        ax1.plot(vix["date"], vix["close"], color=GRUVBOX_RED, label="VIX", linewidth=2)
        ax1.tick_params(axis="y", labelcolor=GRUVBOX_RED)
        ax1.tick_params(axis="x", colors=GRUVBOX_FG)
        ax1.grid(True, color=GRUVBOX_GRAY, alpha=0.3)
        
        # Show one label per month
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.spines['bottom'].set_color(GRUVBOX_FG)
        ax1.spines['top'].set_color(GRUVBOX_FG)
        ax1.spines['left'].set_color(GRUVBOX_RED)
        ax1.spines['right'].set_color(GRUVBOX_FG)
        
        # Gold on right axis - use yellow for precious metal
        ax2 = ax1.twinx()
        ax2.set_ylabel("Gold Price", color=GRUVBOX_YELLOW)
        ax2.plot(gold["date"], gold["close"], color=GRUVBOX_YELLOW, label="Gold", linewidth=2)
        ax2.tick_params(axis="y", labelcolor=GRUVBOX_YELLOW)
        ax2.spines['right'].set_color(GRUVBOX_YELLOW)
        
        fig.suptitle("VIX vs Gold Price (1 Year)", color=GRUVBOX_FG)
        fig.legend(loc="upper left", facecolor=GRUVBOX_BG, labelcolor=GRUVBOX_FG)
        plt.tight_layout()
        
        img_path = REPORTS_DIR / "vix_vs_gold.png"
        fig.savefig(img_path, dpi=300, bbox_inches="tight", facecolor=GRUVBOX_BG)
        plt.close(fig)
        visualizations.append({"title": "VIX vs Gold", "path": str(img_path)})
        logger.info("  Created VIX vs Gold chart")
    except Exception as e:
        logger.error(f"  Error creating VIX vs Gold chart: {e}")
    
    # Create Euribor 12M - €STR Spread chart (90 days)
    try:
        from scripts.utils.caching import load_from_json, CUSTOM_DATA_DIR
        
        euribor = load_from_json("euribor", CUSTOM_DATA_DIR)
        ref_rates = load_from_json("ecb_reference_rates", CUSTOM_DATA_DIR)
        
        if not euribor or not ref_rates:
            logger.warning("  Euribor or ECB reference rates data not available")
        else:
            # Get EURIBOR_12M and ESTR observations
            euribor_12m_obs = euribor.get("history", {}).get("EURIBOR_12M", [])
            estr_obs = ref_rates.get("history", {}).get("ESTR", [])
            
            if not euribor_12m_obs or not estr_obs:
                logger.warning("  EURIBOR_12M or ESTR history not available")
            else:
                # Parse dates and create DataFrames
                euribor_df = pd.DataFrame(euribor_12m_obs)
                estr_df = pd.DataFrame(estr_obs)
                
                # Convert time strings to datetime
                euribor_df["date"] = pd.to_datetime(euribor_df["time"])
                estr_df["date"] = pd.to_datetime(estr_df["time"])
                
                # Merge on date
                merged = pd.merge(euribor_df, estr_df, on="date", suffixes=("_euribor", "_estr"))
                
                # Calculate spread
                merged["spread"] = merged["value_euribor"] - merged["value_estr"]
                
                # Filter to last 365 days to get more data points with monthly data
                cutoff = datetime.now() - timedelta(days=365)
                merged = merged[merged["date"] >= cutoff]
                
                if len(merged) < 2:
                    logger.warning("  Not enough data points for spread chart")
                else:
                    fig, ax = plt.subplots(figsize=(10, 4))
                    
                    # Gruvbox styling
                    fig.patch.set_facecolor(GRUVBOX_BG)
                    ax.set_facecolor(GRUVBOX_BG)
                    ax.plot(merged["date"], merged["spread"], label="Euribor 12M - €STR", color=GRUVBOX_PURPLE, linewidth=2)
                    ax.set_title("Euribor 12M - ECB €STR Spread (1 Year)", color=GRUVBOX_FG)
                    ax.set_xlabel("Date", color=GRUVBOX_FG)
                    ax.set_ylabel("Spread (bps)", color=GRUVBOX_FG)
                    ax.legend(facecolor=GRUVBOX_BG, labelcolor=GRUVBOX_FG)
                    ax.grid(True, color=GRUVBOX_GRAY, alpha=0.3)
                    ax.tick_params(colors=GRUVBOX_FG)
                    ax.spines['bottom'].set_color(GRUVBOX_FG)
                    ax.spines['top'].set_color(GRUVBOX_FG)
                    ax.spines['left'].set_color(GRUVBOX_FG)
                    ax.spines['right'].set_color(GRUVBOX_FG)
                    
                    # Show one label per month to avoid clutter
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    plt.tight_layout()
                    
                    img_path = REPORTS_DIR / "euribor_estr_spread.png"
                    fig.savefig(img_path, dpi=300, bbox_inches="tight", facecolor=GRUVBOX_BG)
                    plt.close(fig)
                    visualizations.append({"title": "Euribor 12M - €STR Spread", "path": str(img_path)})
                    logger.info("  Created Euribor 12M - €STR spread chart")
    except Exception as e:
        logger.error(f"  Error creating Euribor-€STR spread chart: {e}")
    
    return visualizations


def create_html_report(
    snapshot: dict,
    dashboard: dict,
    visualizations: list,
    report_type: str = "daily",
) -> str:
    """Create HTML report content."""
    report_date = format_date(datetime.now(), "%Y-%m-%d %H:%M:%S")
    
    # Traffic light signals
    signals = {
        "vix": get_traffic_light_signal(snapshot["vix"]["value"], THRESHOLDS["vix"]),
        "sp500": get_traffic_light_signal(snapshot["sp500"]["change_1m"], {"red": -5, "yellow": -2}),
        "stoxx600": get_traffic_light_signal(snapshot["stoxx600"]["change_1m"], {"red": -5, "yellow": -2}),
        "msci_world": get_traffic_light_signal(snapshot["msci_world"]["change_1m"], {"red": -5, "yellow": -2}),
        "gold": get_traffic_light_signal(snapshot["gold"]["change_1m"], THRESHOLDS["gold_change"]),
        "brent_crude": get_traffic_light_signal(snapshot["brent_crude"]["change_1m"], THRESHOLDS["gold_change"]),
        "copper": get_traffic_light_signal(snapshot["copper"]["change_1m"], THRESHOLDS["gold_change"]),
        "wheat": get_traffic_light_signal(snapshot["wheat"]["change_1m"], THRESHOLDS["gold_change"]),
        "usd_eur": get_traffic_light_signal(snapshot["usd_eur"]["value"], THRESHOLDS["usd_eur"]),
        "usd_cny": get_traffic_light_signal(snapshot["usd_cny"]["value"], {"red": 7.2, "yellow": 7.0}),
        "us_cpi": get_traffic_light_signal(dashboard["us_cpi"]["value"], THRESHOLDS["cpi"]),
        "us_unemployment": get_traffic_light_signal(dashboard["us_unemployment"]["value"], THRESHOLDS["unemployment"]),
        "eu_cpi": get_traffic_light_signal(dashboard.get("eu_cpi", {}).get("value", 0), THRESHOLDS["cpi"]),
        "eu_unemployment": get_traffic_light_signal(dashboard.get("eu_unemployment", {}).get("value", 0), THRESHOLDS["unemployment"]),
        "spain_cpi": get_traffic_light_signal(dashboard.get("spain_cpi", {}).get("value", 0), THRESHOLDS["cpi"]),
        "spain_unemployment": get_traffic_light_signal(dashboard.get("spain_unemployment", {}).get("value", 0), THRESHOLDS["unemployment"]),
        "treasury_10y": get_traffic_light_signal(dashboard["treasury_10y"]["value"], THRESHOLDS["treasury_10y"]),
        "euribor_12m": get_traffic_light_signal(dashboard.get("euribor_12m", {}).get("value", 0), THRESHOLDS["euribor_12m"]),
        "euribor_12m_estr_spread": get_traffic_light_signal(dashboard.get("euribor_12m_estr_spread", {}).get("value", 0), THRESHOLDS["euribor_12m_estr_spread"]),
        "spain_germany_10y_spread": get_traffic_light_signal(dashboard.get("spain_germany_10y_spread", {}).get("value", 0), THRESHOLDS["spain_germany_10y_spread"]),
        "us_gdp": get_traffic_light_signal(dashboard["us_gdp"]["change_1m"], THRESHOLDS["gdp_growth"]),
        "us_gdp_real": get_traffic_light_signal(dashboard["us_gdp_real"]["change_1m"], THRESHOLDS["gdp_growth"]),
        "us_gdp_yoy": get_traffic_light_signal_higher_better(dashboard.get("us_gdp_yoy", {}).get("value", 0), THRESHOLDS["gdp_yoy"]),
        "eu_gdp_yoy": get_traffic_light_signal_higher_better(dashboard.get("eu_gdp_yoy", {}).get("value", 0), THRESHOLDS["gdp_yoy"]),
        "spain_gdp_yoy": get_traffic_light_signal_higher_better(dashboard.get("spain_gdp_yoy", {}).get("value", 0), THRESHOLDS["gdp_yoy"]),
    }
    
    # Add ECB data signals if available
    for key in dashboard:
        if key.startswith("ecb_yield_") and key not in signals:
            signals[key] = get_traffic_light_signal(dashboard[key]["value"], THRESHOLDS["ecb_yield"])
        elif key.startswith("ecb_") and key not in signals:
            signals[key] = get_traffic_light_signal(dashboard[key]["value"], THRESHOLDS["ecb_rates"])
    
    # Define label mappings (used in both summary and tables)
    macro_labels = {
        "us_cpi": "US CPI",
        "us_unemployment": "US Unemployment",
        "eu_cpi": "EU CPI",
        "eu_unemployment": "EU Unemployment",
        "spain_cpi": "Spain CPI",
        "spain_unemployment": "Spain Unemployment",
        "us_gdp": "US GDP (Nominal)",
        "us_gdp_real": "US GDP (Real)",
        "us_gdp_yoy": "US GDP YoY",
        "eu_gdp_yoy": "EU GDP YoY",
        "spain_gdp_yoy": "Spain GDP YoY",
        "treasury_10y": "US 10Y Treasury",
        "euribor_12m": "Euribor 12M",
        "euribor_12m_estr_spread": "Euribor 12M - €STR Spread",
        "spain_germany_10y_spread": "Spain-Germany 10Y Spread",
        "ecb_yield_1y": "ECB 1Y Yield",
        "ecb_yield_10y": "ECB 10Y Yield",
    }
    
    # Indicator descriptions for tooltips
    indicator_descriptions = {
        "us_cpi": "US Consumer Price Index (CPI) - Year-over-year inflation rate measuring the average change over time in the prices paid by consumers for goods and services. Source: US Bureau of Labor Statistics.",
        "us_unemployment": "US Unemployment Rate - Percentage of the labor force without work but available for and seeking employment. Source: US Bureau of Labor Statistics.",
        "eu_cpi": "Euro Area Consumer Price Index (CPI) - Year-over-year inflation rate for the euro area. Source: Eurostat via ECB.",
        "eu_unemployment": "Euro Area Unemployment Rate - Percentage of the labor force without work. Source: Eurostat.",
        "spain_cpi": "Spain Consumer Price Index (CPI) - Year-over-year inflation rate. Source: Spain INE.",
        "spain_unemployment": "Spain Unemployment Rate - Percentage of the labor force without work. Source: Spain INE.",
        "us_gdp": "US GDP (Nominal) - Gross Domestic Product at current prices in billions. Source: US Bureau of Economic Analysis.",
        "us_gdp_real": "US GDP (Real) - Gross Domestic Product adjusted for inflation. Source: US Bureau of Economic Analysis.",
        "us_gdp_yoy": "US GDP Year-over-Year Growth Rate - Percentage change in real GDP compared to the same quarter in the previous year. Source: US Bureau of Economic Analysis.",
        "eu_gdp_yoy": "EU GDP Year-over-Year Growth Rate - Percentage change in real GDP compared to the same quarter in the previous year. Source: Eurostat.",
        "spain_gdp_yoy": "Spain GDP Year-over-Year Growth Rate - Percentage change in real GDP compared to the same quarter in the previous year. Source: Spain INE.",
        "treasury_10y": "US 10-Year Treasury Yield - Interest rate on US government debt maturing in 10 years. Source: US Treasury.",
        "euribor_12m": "Euribor 12M - 12-month Euribor rate. The rate at which European banks lend to one another. Source: EMMI.",
        "euribor_12m_estr_spread": "Euribor 12M - €STR Spread - Difference between the 12-month Euribor rate and the ECB's Euro Short-Term Rate (€STR). Measures bank lending premium over ECB policy rate.",
        "spain_germany_10y_spread": "Spain-Germany 10Y Sovereign Bond Spread - Difference between Spanish and German 10-year government bond yields. Measures sovereign risk premium.",
        "ecb_yield_1y": "ECB 1-Year Government Bond Yield - Yield on euro area government bonds with 1-year maturity. Source: ECB.",
        "ecb_yield_10y": "ECB 10-Year Government Bond Yield - Yield on euro area government bonds with 10-year maturity. Source: ECB.",
        "sp500": "S&P 500 Index - US stock market index tracking 500 large-cap companies. Source: Yahoo Finance.",
        "stoxx600": "STOXX 600 Index - European stock market index tracking 600 large-cap companies across 17 countries. Source: STOXX.",
        "msci_world": "MSCI World Index - Global stock market index tracking large and mid-cap companies across developed markets. Source: MSCI.",
        "vix": "CBOE Volatility Index (VIX) - Market's expectation of 30-day forward-looking volatility for the S&P 500. Known as the 'fear index'.",
        "gold": "Gold Price - Spot price of gold per ounce. Source: LBMA via Yahoo Finance.",
        "brent_crude": "Brent Crude Oil Price - Spot price of Brent crude oil. Source: ICE via Yahoo Finance.",
        "copper": "Copper Price - Spot price of copper. Source: LME via Yahoo Finance.",
        "wheat": "Wheat Price - Spot price of wheat futures. Source: CBOT via Yahoo Finance.",
        "usd_eur": "USD/EUR Exchange Rate - US Dollar to Euro exchange rate. Source: ECB.",
        "usd_cny": "USD/CNY Exchange Rate - US Dollar to Chinese Yuan exchange rate. Source: ECB.",
    }
    
    # Market snapshot table - label mapping for better display
    metric_labels = {
        "sp500": "S&P 500",
        "stoxx600": "STOXX 600",
        "msci_world": "MSCI World",
        "vix": "VIX",
        "gold": "Gold",
        "brent_crude": "Brent Crude",
        "copper": "Copper",
        "wheat": "Wheat",
        "usd_eur": "USD/EUR",
        "usd_cny": "USD/CNY",
    }
    
    def format_metric(name, value_key, change_1m_key="change_1m", change_1y_key="change_1y", signal_key=None):
        """Helper to format a metric row."""
        val = snapshot[name][value_key]
        chg_1m = snapshot[name].get(change_1m_key, 0)
        chg_1y = snapshot[name].get(change_1y_key, 0)
        sig = signals.get(signal_key or name, "")
        label = metric_labels.get(name, name.replace('_', ' ').title())
        desc = indicator_descriptions.get(name, "")
        tooltip_html = f'<span class="tooltiptext">{desc}</span>' if desc else ''
        return f'<tr class="tooltip-row"><td>{label}{tooltip_html}</td><td>{format_number(val)}</td><td>{format_percentage(chg_1m)}</td><td>{format_percentage(chg_1y)}</td><td>{sig}</td></tr>'
    
    market_table_rows = f"""
    <tr><th>Indicator</th><th>Value</th><th>1M Change</th><th>1Y Change</th><th>Signal</th></tr>
    {format_metric('sp500', 'value', 'change_1m', 'change_1y')}
    {format_metric('stoxx600', 'value', 'change_1m', 'change_1y')}
    {format_metric('msci_world', 'value', 'change_1m', 'change_1y')}
    {format_metric('vix', 'value', 'change_1m', 'change_1y')}
    {format_metric('gold', 'value', 'change_1m', 'change_1y')}
    {format_metric('brent_crude', 'value', 'change_1m', 'change_1y')}
    {format_metric('copper', 'value', 'change_1m', 'change_1y')}
    {format_metric('wheat', 'value', 'change_1m', 'change_1y')}
    {format_metric('usd_eur', 'value', 'change_1m', 'change_1y')}
    {format_metric('usd_cny', 'value', 'change_1m', 'change_1y')}
    """
    
    market_table = f"""
    <h2>📈 Market Snapshot</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; table-layout: fixed;">
        {market_table_rows}
    </table>
    """
    
    # Macroeconomic dashboard - format types
    # GDP values are in absolute terms (billions), not percentages
    macro_value_pct = {
        "us_cpi": True,
        "us_unemployment": True,
        "eu_cpi": True,
        "eu_unemployment": True,
        "spain_cpi": True,
        "spain_unemployment": True,
        "us_gdp": False,
        "us_gdp_real": False,
        "us_gdp_yoy": True,
        "eu_gdp_yoy": True,
        "spain_gdp_yoy": True,
        "treasury_10y": True,
        "euribor_12m": True,
        "euribor_12m_estr_spread": True,
        "spain_germany_10y_spread": True,
        "ecb_yield_1y": True,
        "ecb_yield_10y": True,
    }
    
    def format_macro(name):
        """Helper to format a macroeconomic row."""
        d = dashboard[name]
        is_pct = macro_value_pct.get(name, True)
        val = format_percentage(d["value"], show_sign=False) if is_pct else format_number(d["value"])
        chg_1m = format_percentage(d["change_1m"])
        chg_1y = format_percentage(d["change_1y"], decimals=2) if d.get("change_1y") != 0 else "NA"
        sig = signals.get(name, "")
        label = macro_labels.get(name, name.replace('_', ' ').title())
        desc = indicator_descriptions.get(name, "")
        tooltip_html = f'<span class="tooltiptext">{desc}</span>' if desc else ''
        return f'<tr class="tooltip-row"><td>{label}{tooltip_html}</td><td>{val}</td><td>{chg_1m}</td><td>{chg_1y}</td><td>{sig}</td></tr>'
    
    macro_table_rows = f"""
    <tr><th>Indicator</th><th>Value</th><th>1M Change</th><th>1Y Change</th><th>Signal</th></tr>
    {format_macro('us_cpi')}
    {format_macro('us_unemployment')}
    {format_macro('treasury_10y')}
    """
    
    # Add ECB data if available (grouped with US yields)
    ecb_keys = [
        'ecb_yield_1y', 'ecb_yield_10y',
    ]
    for key in ecb_keys:
        if key in dashboard:
            macro_table_rows += format_macro(key)
    
    # Add Euribor 12M (grouped with ECB data)
    if "euribor_12m" in dashboard:
        macro_table_rows += format_macro('euribor_12m')
    
    # Add Euribor spread (grouped with ECB data)
    if "euribor_12m_estr_spread" in dashboard:
        macro_table_rows += format_macro('euribor_12m_estr_spread')
    
    # Add EU and Spain data if available (grouped together) - excluding GDP YoY
    eu_spain_keys = [
        'eu_cpi', 'eu_unemployment',
        'spain_cpi', 'spain_unemployment',
        'spain_germany_10y_spread'
    ]
    for key in eu_spain_keys:
        if key in dashboard:
            macro_table_rows += format_macro(key)
    
    macro_table = f"""
    <h2>🏛️ Macroeconomic Dashboard</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; table-layout: fixed;">
        {macro_table_rows}
    </table>
    """
    
    # GDP YoY separate table (no 1M Change column)
    def format_gdp_yoy(name):
        """Helper to format a GDP YoY row with only value and signal."""
        d = dashboard[name]
        is_pct = macro_value_pct.get(name, True)
        val = format_percentage(d["value"], show_sign=False) if is_pct else format_number(d["value"])
        sig = signals.get(name, "")
        label = macro_labels.get(name, name.replace('_', ' ').title())
        desc = indicator_descriptions.get(name, "")
        tooltip_html = f'<span class="tooltiptext">{desc}</span>' if desc else ''
        return f'<tr class="tooltip-row"><td>{label}{tooltip_html}</td><td>{val}</td><td>{sig}</td></tr>'
    
    gdp_yoy_rows = """
    <tr><th>Indicator</th><th>Value</th><th>Signal</th></tr>
    """
    gdp_yoy_keys = ['us_gdp_yoy', 'eu_gdp_yoy', 'spain_gdp_yoy']
    for key in gdp_yoy_keys:
        if key in dashboard and dashboard[key].get('value', 0) > 0:
            gdp_yoy_rows += format_gdp_yoy(key)
    
    gdp_yoy_table = f"""
    <h2>📊 GDP Year-over-Year Growth</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; table-layout: fixed;">
        {gdp_yoy_rows}
    </table>
    """
    
    # Spanish Real Estate table
    real_estate_labels = {
        "avg_mortgage_rate": "Average Mortgage Interest Rate",
        "new_mortgage_loans_count": "New Mortgage Loans (Count)",
        "new_mortgage_loans_value": "New Mortgage Loans (Value)",
        "house_price_index": "House Price Index (IPV)",
        "fixed_vs_variable_rate_share": "Fixed vs. Variable Rate Share",
        "mortgage_approval_time": "Mortgage Average Term",
    }
    
    real_estate_value_pct = {
        "avg_mortgage_rate": True,
        "new_mortgage_loans_count": False,
        "new_mortgage_loans_value": False,
        "house_price_index": False,
        "fixed_vs_variable_rate_share": True,
        "mortgage_approval_time": False,
    }
    
    def format_real_estate(name):
        """Helper to format a real estate row."""
        d = real_estate_data.get("indicators", {}).get(name, {})
        is_pct = real_estate_value_pct.get(name, True)
        val = format_percentage(d.get("value"), show_sign=False) if is_pct else format_number(d.get("value"))
        chg_1m = format_percentage(d.get("change_1m"))
        chg_1y = format_percentage(d.get("change_1y"))
        label = real_estate_labels.get(name, name.replace('_', ' ').title())
        unit = d.get("unit", "")
        desc = d.get("description", "")
        source = d.get("source", "")
        full_desc = f"{desc} - {source}" if source else desc
        tooltip_html = f'<span class="tooltiptext">{full_desc}</span>' if full_desc else ''
        # Only add space and unit if unit is not empty and value is not NA
        unit_display = f" {unit}" if (unit and val != "NA") else ""
        return f'<tr class="tooltip-row"><td>{label}{tooltip_html}</td><td>{val}{unit_display}</td><td>{chg_1m}</td><td>{chg_1y}</td></tr>'
    
    # Load Spanish real estate data
    try:
        from scripts.utils.caching import load_from_json, CUSTOM_DATA_DIR
        real_estate_data = load_from_json("spanish_real_estate", CUSTOM_DATA_DIR)
    except Exception:
        real_estate_data = {"indicators": {}}
    
    real_estate_table_rows = """
    <tr><th>Indicator</th><th>Value</th><th>1M Change</th><th>1Y Change</th></tr>
    """
    
    real_estate_keys = [
        "house_price_index",
        "avg_mortgage_rate",
        "new_mortgage_loans_count",
        "new_mortgage_loans_value",
        "fixed_vs_variable_rate_share",
        "mortgage_approval_time",
    ]
    
    for key in real_estate_keys:
        if key in real_estate_data.get("indicators", {}):
            real_estate_table_rows += format_real_estate(key)
    
    real_estate_table = f"""
    <h2>🏠 Spanish Real Estate</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; table-layout: fixed;">
        {real_estate_table_rows}
    </table>
    """
    
    # Visualizations
    viz_html = ""
    for viz in visualizations:
        viz_html += f"""
        <div style="margin: 40px 0;">
            <h3>{viz['title']}</h3>
            <img src="{image_to_data_uri(viz['path'])}" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px;" alt="{viz['title']}">
        </div>
        """
    
    # CSS styling - Gruvbox Dark theme with JetBrains Mono font
    css = """
    <style>
        @font-face {
            font-family: 'JetBrains Mono';
            src: url('/Users/bengui/Downloads/JetBrainsMono-2.304/fonts/ttf/JetBrainsMono-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'JetBrains Mono';
            src: url('/Users/bengui/Downloads/JetBrainsMono-2.304/fonts/ttf/JetBrainsMono-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        
        body {
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #282828;
            color: #ebdbb2;
        }
        h1 {
            color: #fabd2f;
            border-bottom: 2px solid #83a598;
            padding-bottom: 10px;
        }
        h2 {
            color: #b8bb26;
            margin-top: 30px;
            border-bottom: 1px solid #504945;
            padding-bottom: 5px;
        }
        h3 {
            color: #83a598;
        }
        p, .em { color: #d4be98; }
        table {
            border: 1px solid #504945;
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #504945;
        }
        /* 5-column table (Market Snapshot) */
        table:nth-of-type(1) th:nth-child(1),
        table:nth-of-type(1) td:nth-child(1) { width: 30%; }
        table:nth-of-type(1) th:nth-child(2),
        table:nth-of-type(1) td:nth-child(2) { width: 20%; }
        table:nth-of-type(1) th:nth-child(3),
        table:nth-of-type(1) td:nth-child(3) { width: 15%; }
        table:nth-of-type(1) th:nth-child(4),
        table:nth-of-type(1) td:nth-child(4) { width: 15%; }
        table:nth-of-type(1) th:nth-child(5),
        table:nth-of-type(1) td:nth-child(5) { width: 20%; }
        /* 5-column table (Macroeconomic Dashboard) */
        table:nth-of-type(2) th:nth-child(1),
        table:nth-of-type(2) td:nth-child(1) { width: 30%; }
        table:nth-of-type(2) th:nth-child(2),
        table:nth-of-type(2) td:nth-child(2) { width: 20%; }
        table:nth-of-type(2) th:nth-child(3),
        table:nth-of-type(2) td:nth-child(3) { width: 15%; }
        table:nth-of-type(2) th:nth-child(4),
        table:nth-of-type(2) td:nth-child(4) { width: 15%; }
        table:nth-of-type(2) th:nth-child(5),
        table:nth-of-type(2) td:nth-child(5) { width: 20%; }
        /* 3-column table (GDP YoY) */
        table:nth-of-type(3) th:nth-child(1),
        table:nth-of-type(3) td:nth-child(1) { width: 50%; }
        table:nth-of-type(3) th:nth-child(2),
        table:nth-of-type(3) td:nth-child(2) { width: 25%; }
        table:nth-of-type(3) th:nth-child(3),
        table:nth-of-type(3) td:nth-child(3) { width: 25%; }
        /* 4-column table (Spanish Real Estate) */
        table:nth-of-type(4) th:nth-child(1),
        table:nth-of-type(4) td:nth-child(1) { width: 40%; }
        table:nth-of-type(4) th:nth-child(2),
        table:nth-of-type(4) td:nth-child(2) { width: 20%; }
        table:nth-of-type(4) th:nth-child(3),
        table:nth-of-type(4) td:nth-child(3) { width: 20%; }
        table:nth-of-type(4) th:nth-child(4),
        table:nth-of-type(4) td:nth-child(4) { width: 20%; }
        th {
            background-color: #458588;
            color: #282828;
            font-weight: bold;
        }
        tr:nth-child(even) { background-color: #3c3836; }
        tr:nth-child(odd) { background-color: #282828; }
        tr:hover { background-color: #504945; }
        /* Tooltip styling */
        .tooltip-row {
            position: relative;
        }
        .tooltip-row td:first-child {
            position: relative;
        }
        .tooltiptext {
            visibility: hidden;
            width: 300px;
            background-color: #3c3836;
            color: #ebdbb2;
            text-align: left;
            border-radius: 5px;
            border: 1px solid #504945;
            padding: 10px;
            position: absolute;
            z-index: 1000;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 14px;
            line-height: 1.4;
        }
        .tooltip-row:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        /* Signal colors - use gruvbox palette */
        .signal-red { color: #fb4934; font-weight: bold; }
        .signal-yellow { color: #fabd2f; font-weight: bold; }
        .signal-green { color: #b8bb26; font-weight: bold; }
        
        /* Executive summary styling */
        .exec-summary {
            background-color: #3c3836;
            padding: 20px;
            border-radius: 5px;
            border: 1px solid #504945;
        }
        
        /* Visualizations */
        .viz-container {
            background-color: #3c3836;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border: 1px solid #504945;
        }
        
        /* Legend */
        .legend-box {
            background-color: #3c3836;
            margin-top: 40px;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #504945;
        }
        
        .meta { color: #83a598; text-align: center; margin-bottom: 20px; }
        
        a { color: #83a598; text-decoration: none; }
        a:hover { text-decoration: underline; }

        /* ----- Mobile / responsive ----- */
        @media (max-width: 768px) {
            body {
                padding: 12px;
                padding-top: max(12px, env(safe-area-inset-top));
                font-size: 13px;
            }
            h1 { font-size: 1.5em; padding-bottom: 8px; }
            h2 { font-size: 1.2em; margin-top: 24px; }
            h3 { font-size: 1.05em; }

            /* Tables become horizontally scrollable so wide dashboards stay
               readable instead of overflowing the viewport. */
            table {
                display: block;
                overflow-x: auto;
                white-space: nowrap;
                -webkit-overflow-scrolling: touch;
                table-layout: auto;
            }
            th, td {
                padding: 8px 10px;
            }

            /* Tooltips rely on hover and are unreliable on touch. Hide them on
               mobile; the underlying data is still visible in the table cells. */
            .tooltiptext { display: none !important; }

            .exec-summary, .viz-container, .legend-box {
                padding: 12px;
            }
        }
    </style>
    """
    
    # Full HTML report
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Macro Economic Financial Report - {report_date}</title>
    {css}
</head>
<body>
    <h1>Macro Economic Financial Report</h1>
    <p class="meta"><em>Report Type: {report_type.capitalize()} | Generated: {report_date}</em></p>
    
    {market_table}
    
    {macro_table}
    
    {gdp_yoy_table}
    
    {real_estate_table}
    
    <h2>📊 Visualizations</h2>
    <div class="viz-container">
    {viz_html}
    </div>
    
    <div class="legend-box">
        <h3>Legend</h3>
        <p><span class="signal-red">🔴</span> = Red (High Risk/Warning) | 
           <span class="signal-yellow">🟡</span> = Yellow (Caution) | 
           <span class="signal-green">🟢</span> = Green (Normal)</p>
    </div>
    
</body>
</html>
"""
    
    return html


def save_html_report(html: str, report_type: str = "daily") -> Path:
    """Save HTML report to file."""
    filename = f"{report_type}_report.html"
    filepath = REPORTS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


def save_pdf_report(html: str, report_type: str = "daily") -> Path | None:
    """Save PDF report using WeasyPrint."""
    try:
        from weasyprint import HTML
        filename = f"{report_type}_report.pdf"
        filepath = REPORTS_DIR / filename
        HTML(string=html).write_pdf(filepath)
        return filepath
    except ImportError:
        logger.error("WeasyPrint not installed. Cannot generate PDF.")
        return None
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return None

def publish_report(report_type: str = "daily") -> Path | None:
    """Publish the generated HTML report to the GitHub Pages site root.

    Copies ``reports/{report_type}_report.html`` to ``docs/index.html`` so it
    is served as the GitHub Pages landing page and refreshed whenever the
    report is regenerated.
    """
    source = REPORTS_DIR / f"{report_type}_report.html"
    if not source.exists():
        logger.error(f"Cannot publish: source report not found: {source}")
        return None

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    destination = PAGES_DIR / "index.html"
    shutil.copy2(source, destination)
    logger.info(f"  Published report to GitHub Pages site root: {destination}")
    return destination


def generate_report(report_type: str = "daily", output_format: str = "both", publish: bool = False) -> None:
    """Generate financial report."""
    logger.info("=" * 60)
    logger.info(f"Generating {report_type} report")
    logger.info("=" * 60)
    
    # Create data
    logger.info("Creating market snapshot...")
    snapshot = create_market_snapshot()
    
    logger.info("Creating macro dashboard...")
    dashboard = create_macro_dashboard()
    
    logger.info("Creating visualizations...")
    visualizations = create_visualizations(snapshot, dashboard)
    
    # Create HTML
    logger.info("Creating HTML report...")
    html = create_html_report(snapshot, dashboard, visualizations, report_type)
    
    # Save reports
    if output_format in ("html", "both"):
        html_path = save_html_report(html, report_type)
        logger.info(f"  Saved HTML report: {html_path}")
    
    if output_format in ("pdf", "both"):
        pdf_path = save_pdf_report(html, report_type)
        if pdf_path:
            logger.info(f"  Saved PDF report: {pdf_path}")
    
    if publish:
        publish_report(report_type)

    logger.info("=" * 60)
    logger.info("Report generation completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate macroeconomic financial report")
    parser.add_argument(
        "--type",
        type=str,
        default="daily",
        choices=["daily", "weekly"],
        help="Report type (default: daily)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="both",
        choices=["html", "pdf", "both"],
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish the HTML report to the GitHub Pages site root (docs/index.html)",
    )
    args = parser.parse_args()

    generate_report(args.type, args.output, publish=args.publish)
