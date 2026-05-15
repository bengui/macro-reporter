#!/usr/bin/env python3
"""
Generate macroeconomic financial report from cached data.

This script loads data from the cache and generates a PDF/HTML report
with executive summary, market snapshot, macroeconomic dashboard, and visualizations.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    OPENBB_DATA_DIR,
    CUSTOM_DATA_DIR,
)
from scripts.utils.formatting import (
    format_number,
    format_percentage,
    format_date,
    format_change,
    get_traffic_light_signal,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("generate_report")

# Configuration
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Traffic light thresholds
THRESHOLDS = {
    "vix": {"red": 20, "yellow": 15},
    "sp500_change": {"red": -5, "yellow": -2, "green": 2},  # Negative thresholds
    "gold_change": {"red": -5, "yellow": -2},
    "usd_eur": {"red": 1.15, "yellow": 1.10},  # EUR/USD rate
    "cpi": {"red": 4.0, "yellow": 2.5},  # Inflation rate
    "unemployment": {"red": 6.0, "yellow": 4.5},  # Unemployment rate
    "treasury_10y": {"red": 5.0, "yellow": 4.0},  # 10Y Treasury yield
    "euribor_3m": {"red": 4.0, "yellow": 3.0},  # Euribor 3M rate
    "gdp_growth": {"red": -1.0, "yellow": 1.5},  # GDP growth rate
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
            }
        except Exception as e:
            logger.warning(f"Error loading {name.replace('_', ' ').title()}: {e}")
            snapshot[name] = {"value": 0, "change_1m": 0}
    
    # Forex
    forex = ["usd_eur", "usd_cny"]
    for name in forex:
        try:
            df = load_from_csv(name)
            snapshot[name] = {
                "value": get_latest_value(df, "close"),
                "change_1m": calculate_change(df, "close", 30),
            }
        except Exception as e:
            logger.warning(f"Error loading {name.upper()}: {e}")
            snapshot[name] = {"value": 0, "change_1m": 0}
    
    return snapshot


def create_macro_dashboard() -> dict:
    """Create macroeconomic dashboard data."""
    dashboard = {}
    
    # CPI
    try:
        cpi = load_from_csv("us_cpi")
        latest = get_latest_value(cpi)
        dashboard["us_cpi"] = {
            "value": latest,
            "previous": get_previous_value(cpi, days=30),
            "change_1m": calculate_change(cpi, days=30),
        }
    except Exception as e:
        logger.warning(f"Error loading US CPI: {e}")
        dashboard["us_cpi"] = {"value": 0, "previous": 0, "change_1m": 0}
    
    # Unemployment
    try:
        unemployment = load_from_csv("us_unemployment")
        latest = get_latest_value(unemployment)
        dashboard["us_unemployment"] = {
            "value": latest,
            "previous": get_previous_value(unemployment, days=30),
            "change_1m": calculate_change(unemployment, days=30),
        }
    except Exception as e:
        logger.warning(f"Error loading US Unemployment: {e}")
        dashboard["us_unemployment"] = {"value": 0, "previous": 0, "change_1m": 0}
    
    # GDP (nominal)
    try:
        gdp = load_from_csv("us_gdp")
        latest = get_latest_value(gdp)
        dashboard["us_gdp"] = {
            "value": latest,
            "previous": get_previous_value(gdp, days=90),  # Quarterly data
            "change_1m": calculate_change(gdp, days=90),
        }
    except Exception as e:
        logger.warning(f"Error loading US GDP: {e}")
        dashboard["us_gdp"] = {"value": 0, "previous": 0, "change_1m": 0}
    
    # GDP Real
    try:
        gdp_real = load_from_csv("us_gdp_real")
        latest = get_latest_value(gdp_real)
        dashboard["us_gdp_real"] = {
            "value": latest,
            "previous": get_previous_value(gdp_real, days=90),  # Quarterly data
            "change_1m": calculate_change(gdp_real, days=90),
        }
    except Exception as e:
        logger.warning(f"Error loading US GDP Real: {e}")
        dashboard["us_gdp_real"] = {"value": 0, "previous": 0, "change_1m": 0}
    
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
                if obs_list and len(obs_list) >= 2:
                    # Observations are sorted oldest first, newest last
                    # First element is ~30 days ago, last element is most recent (same as 'value')
                    prev_val = obs_list[0]["value"]
                    # Calculate change from first to last observation
                    if prev_val != 0:
                        change_1m = ((value - prev_val) / abs(prev_val)) * 100
                dashboard[f"ecb_yield_{maturity.lower()}"] = {
                    "value": value,
                    "previous": prev_val,
                    "change_1m": change_1m,
                }
    except Exception as e:
        logger.warning(f"Error loading ECB yield curve: {e}")
    
    # ECB Reference Rates (from custom data)
    try:
        ref_rates = load_from_json("ecb_reference_rates", CUSTOM_DATA_DIR)
        if "rates" in ref_rates and isinstance(ref_rates["rates"], dict):
            history = ref_rates.get("history", {})
            for name, value in ref_rates["rates"].items():
                prev_val = 0
                change_1m = 0
                # Get historical observations for this rate
                obs_list = history.get(name, [])
                if obs_list and len(obs_list) >= 2:
                    # Observations are sorted oldest first, newest last
                    prev_val = obs_list[0]["value"]
                    # Calculate change from first to last observation
                    if prev_val != 0:
                        change_1m = ((value - prev_val) / abs(prev_val)) * 100
                dashboard[f"ecb_{name.lower()}"] = {
                    "value": value,
                    "previous": prev_val,
                    "change_1m": change_1m,
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
            dashboard["treasury_10y"] = {
                "value": latest,
                "previous": previous,
                "change_1m": change,
            }
        else:
            # Try to find any column with '10' in it
            for col in treasury.columns:
                if "10" in str(col).lower():
                    latest = get_latest_value(treasury, col) * 100
                    previous = get_previous_value(treasury, col, 30) * 100
                    change = calculate_change(treasury, col, 30)
                    dashboard["treasury_10y"] = {
                        "value": latest,
                        "previous": previous,
                        "change_1m": change,
                    }
                    break
            else:
                dashboard["treasury_10y"] = {"value": 0, "previous": 0, "change_1m": 0}
    except Exception as e:
        logger.warning(f"Error loading Treasury rates: {e}")
        dashboard["treasury_10y"] = {"value": 0, "previous": 0, "change_1m": 0}
    
    # Euribor rates (from custom data)
    try:
        euribor = load_from_json("euribor", CUSTOM_DATA_DIR)
        if "rates" in euribor and isinstance(euribor["rates"], dict):
            history = euribor.get("history", {})
            # Get 3M Euribor as the primary indicator
            if "EURIBOR_3M" in euribor["rates"]:
                value = euribor["rates"]["EURIBOR_3M"]
                prev_val = 0
                change_1m = 0
                # Get historical observations for 3M
                obs_list = history.get("EURIBOR_3M", [])
                if obs_list and len(obs_list) >= 2:
                    # Observations are sorted oldest first, newest last
                    prev_val = obs_list[0]["value"]
                    if prev_val != 0:
                        change_1m = ((value - prev_val) / abs(prev_val)) * 100
                dashboard["euribor_3m"] = {
                    "value": value,
                    "previous": prev_val,
                    "change_1m": change_1m,
                }
            else:
                # Try to find any 3M rate
                for key, value in euribor["rates"].items():
                    if "3M" in key or "3MONTH" in key:
                        prev_val = 0
                        change_1m = 0
                        obs_list = history.get(key, [])
                        if obs_list and len(obs_list) >= 2:
                            prev_val = obs_list[0]["value"]
                            if prev_val != 0:
                                change_1m = ((value - prev_val) / abs(prev_val)) * 100
                        dashboard["euribor_3m"] = {
                            "value": value,
                            "previous": prev_val,
                            "change_1m": change_1m,
                        }
                        break
                else:
                    dashboard["euribor_3m"] = {"value": 0, "previous": 0, "change_1m": 0}
        else:
            dashboard["euribor_3m"] = {"value": 0, "previous": 0, "change_1m": 0}
    except Exception as e:
        logger.warning(f"Error loading Euribor rates: {e}")
        dashboard["euribor_3m"] = {"value": 0, "previous": 0, "change_1m": 0}
    
    return dashboard


def create_visualizations(snapshot: dict, dashboard: dict) -> list:
    """Create matplotlib visualizations and save as images."""
    visualizations = []
    
    # Create sp500 trend chart
    try:
        sp500 = load_from_csv("sp500")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sp500["date"], sp500["close"], label="S&P 500")
        ax.set_title("S&P 500 Price Trend (Last 90 Days)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.legend()
        ax.grid(True)
        # Reduce x-axis label density to avoid overlap
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(10))
        plt.tight_layout()
        
        img_path = REPORTS_DIR / "sp500_trend.png"
        fig.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        visualizations.append({"title": "S&P 500 Trend", "path": str(img_path)})
        logger.info(f"  Created S&P 500 trend chart")
    except Exception as e:
        logger.error(f"  Error creating S&P 500 chart: {e}")
    
    # Create VIX vs Gold chart
    try:
        vix = load_from_csv("vix")
        gold = load_from_csv("gold")
        
        fig, ax1 = plt.subplots(figsize=(10, 4))
        
        color = "tab:blue"
        ax1.set_xlabel("Date")
        ax1.set_ylabel("VIX", color=color)
        ax1.plot(vix["date"], vix["close"], color=color, label="VIX")
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.grid(True)
        # Reduce x-axis label density to avoid overlap
        ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(10))
        
        ax2 = ax1.twinx()
        color = "tab:orange"
        ax2.set_ylabel("Gold Price", color=color)
        ax2.plot(gold["date"], gold["close"], color=color, label="Gold")
        ax2.tick_params(axis="y", labelcolor=color)
        
        fig.suptitle("VIX vs Gold Price")
        fig.legend(loc="upper left")
        plt.tight_layout()
        
        img_path = REPORTS_DIR / "vix_vs_gold.png"
        fig.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        visualizations.append({"title": "VIX vs Gold", "path": str(img_path)})
        logger.info(f"  Created VIX vs Gold chart")
    except Exception as e:
        logger.error(f"  Error creating VIX vs Gold chart: {e}")
    
    return visualizations


def create_html_report(
    snapshot: dict,
    dashboard: dict,
    visualizations: list,
    report_type: str = "daily",
) -> str:
    """Create HTML report content."""
    report_date = format_date(datetime.now())
    
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
        "treasury_10y": get_traffic_light_signal(dashboard["treasury_10y"]["value"], THRESHOLDS["treasury_10y"]),
        "euribor_3m": get_traffic_light_signal(dashboard["euribor_3m"]["value"], THRESHOLDS["euribor_3m"]),
        "us_gdp": get_traffic_light_signal(dashboard["us_gdp"]["change_1m"], THRESHOLDS["gdp_growth"]),
        "us_gdp_real": get_traffic_light_signal(dashboard["us_gdp_real"]["change_1m"], THRESHOLDS["gdp_growth"]),
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
        "us_gdp": "US GDP (Nominal)",
        "us_gdp_real": "US GDP (Real)",
        "treasury_10y": "US 10Y Treasury",
        "euribor_3m": "Euribor 3M",
        "ecb_yield_2y": "ECB 2Y Yield",
        "ecb_yield_5y": "ECB 5Y Yield",
        "ecb_yield_10y": "ECB 10Y Yield",
        "ecb_yield_30y": "ECB 30Y Yield",
        "ecb_estr": "ECB €STR",
    }
    
    # Executive summary
    executive_summary = f"""
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h2>Executive Summary - {report_date}</h2>
        <p style="font-size: 16px; line-height: 1.6;">
            The S&P 500 is currently at {format_number(snapshot['sp500']['value'])} 
            ({format_percentage(snapshot['sp500']['change_1m'])} over the past month). 
            Market volatility as measured by the VIX stands at {format_number(snapshot['vix']['value'])} 
            ({signals['vix']}). 
            STOXX 600 at {format_number(snapshot['stoxx600']['value'])} 
            ({format_percentage(snapshot['stoxx600']['change_1m'])}). 
            Gold prices have moved {format_percentage(snapshot['gold']['change_1m'])} 
            over the past month to {format_number(snapshot['gold']['value'])}.
        </p>
        <p style="font-size: 16px; line-height: 1.6; margin-top: 10px;">
            US inflation (CPI) is at {format_percentage(dashboard['us_cpi']['value'])} 
            ({signals['us_cpi']}), while the unemployment rate stands at {format_percentage(dashboard['us_unemployment']['value'])} 
            ({signals['us_unemployment']}). 
            US GDP (Nominal) at {format_number(dashboard['us_gdp']['value'])} 
            ({signals['us_gdp']}), Real GDP at {format_number(dashboard['us_gdp_real']['value'])} 
            ({signals['us_gdp_real']}).
        </p>
        """
    
    # Add Euribor info if available
    if dashboard.get("euribor_3m") and dashboard["euribor_3m"]["value"] > 0:
        executive_summary += f"""
        <p style="font-size: 16px; line-height: 1.6; margin-top: 10px;">
            Euribor 3-month rate is at {format_percentage(dashboard['euribor_3m']['value'])} 
            ({signals['euribor_3m']}). 
            US 10Y Treasury yield at {format_percentage(dashboard['treasury_10y']['value'])} 
            ({signals['treasury_10y']}).
        </p>
        """
    
    # Add ECB yield curve info if available
    ecb_yields = [k for k in dashboard.keys() if k.startswith("ecb_yield_")]
    if ecb_yields:
        yield_items = []
        for k in ecb_yields:
            label = macro_labels.get(k, k.replace('_', ' ').title())
            sig = signals.get(k, '')
            yield_items.append(f"{label} {format_percentage(dashboard[k]['value'])} ({sig})")
        executive_summary += f"""
        <p style="font-size: 16px; line-height: 1.6; margin-top: 10px;">
            Euro area yield curve: {', '.join(yield_items)}.
        </p>
        """
    
    # Add ECB reference rates info if available
    ecb_rates = [k for k in dashboard.keys() if k.startswith("ecb_") and not k.startswith("ecb_yield_")]
    if ecb_rates:
        rate_items = []
        for k in ecb_rates:
            label = macro_labels.get(k, k.replace('_', ' ').title())
            sig = signals.get(k, '')
            rate_items.append(f"{label} {format_percentage(dashboard[k]['value'])} ({sig})")
        executive_summary += f"""
        <p style="font-size: 16px; line-height: 1.6; margin-top: 10px;">
            ECB reference rates: {', '.join(rate_items)}.
        </p>
        """
    
    executive_summary += "</div>"
    
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
    
    def format_metric(name, value_key, change_key="change_1m", signal_key=None):
        """Helper to format a metric row."""
        val = snapshot[name][value_key]
        chg = snapshot[name].get(change_key, 0)
        sig = signals.get(signal_key or name, "")
        label = metric_labels.get(name, name.replace('_', ' ').title())
        return f"<tr><td>{label}</td><td>{format_number(val)}</td><td>{format_percentage(chg)}</td><td>{sig}</td></tr>"
    
    market_table_rows = f"""
    <tr><th>Metric</th><th>Value</th><th>1M Change</th><th>Signal</th></tr>
    {format_metric('sp500', 'value', 'change_1m')}
    {format_metric('stoxx600', 'value', 'change_1m')}
    {format_metric('msci_world', 'value', 'change_1m')}
    {format_metric('vix', 'value', 'change_1m')}
    {format_metric('gold', 'value', 'change_1m')}
    {format_metric('brent_crude', 'value', 'change_1m')}
    {format_metric('copper', 'value', 'change_1m')}
    {format_metric('wheat', 'value', 'change_1m')}
    {format_metric('usd_eur', 'value', 'change_1m')}
    {format_metric('usd_cny', 'value', 'change_1m')}
    """
    
    market_table = f"""
    <h2>📈 Market Snapshot</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        {market_table_rows}
    </table>
    """
    
    # Macroeconomic dashboard - format types
    # GDP values are in absolute terms (billions), not percentages
    macro_value_pct = {
        "us_cpi": True,
        "us_unemployment": True,
        "us_gdp": False,
        "us_gdp_real": False,
        "treasury_10y": True,
        "euribor_3m": True,
        "ecb_yield_2y": True,
        "ecb_yield_5y": True,
        "ecb_yield_10y": True,
        "ecb_yield_30y": True,
        "ecb_estr": True,
    }
    
    def format_macro(name):
        """Helper to format a macroeconomic row."""
        d = dashboard[name]
        is_pct = macro_value_pct.get(name, True)
        val = format_percentage(d["value"]) if is_pct else format_number(d["value"])
        prev = format_percentage(d["previous"]) if is_pct else format_number(d["previous"])
        chg = format_percentage(d["change_1m"])
        sig = signals.get(name, "")
        label = macro_labels.get(name, name.replace('_', ' ').title())
        return f"<tr><td>{label}</td><td>{val}</td><td>{prev}</td><td>{chg}</td><td>{sig}</td></tr>"
    
    macro_table_rows = f"""
    <tr><th>Indicator</th><th>Value</th><th>Previous</th><th>1M Change</th><th>Signal</th></tr>
    {format_macro('us_cpi')}
    {format_macro('us_unemployment')}
    {format_macro('us_gdp')}
    {format_macro('us_gdp_real')}
    {format_macro('treasury_10y')}
    {format_macro('euribor_3m')}
    """
    
    # Add ECB data if available
    ecb_keys = [
        'ecb_yield_2y', 'ecb_yield_5y', 'ecb_yield_10y', 'ecb_yield_30y',
        'ecb_estr'
    ]
    for key in ecb_keys:
        if key in dashboard:
            macro_table_rows += format_macro(key)
    
    macro_table = f"""
    <h2>🏛️ Macroeconomic Dashboard</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        {macro_table_rows}
    </table>
    """
    
    # Visualizations
    viz_html = ""
    for viz in visualizations:
        viz_html += f"""
        <div style="margin: 40px 0;">
            <h3>{viz['title']}</h3>
            <img src="{viz['path']}" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px;">
        </div>
        """
    
    # CSS styling
    css = """
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        h3 { color: #7f8c8d; }
        table { border: 1px solid #ddd; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #3498db; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .signal-red { color: #e74c3c; font-weight: bold; }
        .signal-yellow { color: #f39c12; font-weight: bold; }
        .signal-green { color: #27ae60; font-weight: bold; }
    </style>
    """
    
    # Full HTML report
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Macro Economic Financial Report - {report_date}</title>
    {css}
</head>
<body>
    <h1>Macro Economic Financial Report</h1>
    <p><em>Report Type: {report_type.capitalize()} | Generated: {report_date}</em></p>
    
    {executive_summary}
    
    {market_table}
    
    {macro_table}
    
    <h2>📊 Visualizations</h2>
    {viz_html}
    
    <div style="margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
        <h3>Legend</h3>
        <p><span style="color: #e74c3c; font-weight: bold;">🔴</span> = Red (High Risk/Warning) | 
           <span style="color: #f39c12; font-weight: bold;">🟡</span> = Yellow (Caution) | 
           <span style="color: #27ae60; font-weight: bold;">🟢</span> = Green (Normal)</p>
    </div>
    
</body>
</html>
"""
    
    return html


def save_html_report(html: str, report_type: str = "daily") -> Path:
    """Save HTML report to file."""
    filename = f"{report_type}_report_{datetime.now().strftime('%Y-%m-%d')}.html"
    filepath = REPORTS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


def save_pdf_report(html: str, report_type: str = "daily") -> Path:
    """Save PDF report using WeasyPrint."""
    try:
        from weasyprint import HTML
        filename = f"{report_type}_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        filepath = REPORTS_DIR / filename
        HTML(string=html).write_pdf(filepath)
        return filepath
    except ImportError:
        logger.error("WeasyPrint not installed. Cannot generate PDF.")
        return None
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return None


def generate_report(report_type: str = "daily", output_format: str = "both") -> None:
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
    args = parser.parse_args()
    
    generate_report(args.type, args.output)
