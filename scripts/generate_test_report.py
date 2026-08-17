#!/usr/bin/env python3
"""
Generate a local test report from deterministic mock data.

This script writes a fixed set of mock macroeconomic data into the local
cache directories (``data/openbb_data`` and ``data/custom_data``) and then
runs the real report-generation pipeline against it. It makes **no network
requests**, so it can be used to verify UI / report-logic changes offline.

The mock values are intentionally chosen to exercise the full report: every
market snapshot row, macro dashboard row, GDP YoY row, real-estate row, and
every visualization renders from this data.

Usage:
    uv run python scripts/generate_test_report.py
    uv run python scripts/generate_test_report.py --type weekly --output html
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_report import generate_report
from scripts.utils.caching import (
    CUSTOM_DATA_DIR,
    OPENBB_DATA_DIR,
    save_to_csv,
    save_to_json,
)
from scripts.utils.logging import setup_logging

logger = setup_logging("generate_test_report")


def _date_series(days: int) -> list[str]:
    """Return ``days`` ISO date strings ending today.

    Dates are relative to the current runtime date so the report's
    last-365-days chart filters keep the data points.
    """
    end = datetime.now(timezone.utc)
    return [(end - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days - 1, -1, -1)]


def _monthly_series(months: int) -> list[str]:
    """Return month-start ISO date strings ending at the current month."""
    end = datetime.now(timezone.utc).replace(day=1)
    out: list[str] = []
    for m in range(months - 1, -1, -1):
        year = end.year - ((end.month - 1 - m) // 12)
        month = (end.month - 1 - m) % 12 + 1
        out.append(datetime(year, month, 1, tzinfo=timezone.utc).strftime("%Y-%m-%d"))
    return out


def _trend(start: float, end: float, n: int) -> list[float]:
    """Linear interpolation from ``start`` to ``end`` over ``n`` points."""
    if n <= 1:
        return [end]
    return [start + (end - start) * i / (n - 1) for i in range(n)]


def _write_market_data() -> None:
    """Write mock CSVs for market indices, commodities and forex."""
    days = 400
    dates = _date_series(days)

    # name -> (start close, end close)
    series = {
        "sp500": (4200.0, 5460.0),
        "stoxx600": (450.0, 515.0),
        "msci_world": (95.0, 108.0),
        "vix": (22.0, 13.5),
        "gold": (1900.0, 2320.0),
        "brent_crude": (74.0, 85.0),
        "copper": (3.8, 4.4),
        "wheat": (620.0, 575.0),
        "usd_eur": (1.08, 1.085),
        "usd_cny": (7.15, 7.24),
    }
    for name, (start, end) in series.items():
        closes = _trend(start, end, days)
        df = pd.DataFrame({"date": dates, "close": closes})
        save_to_csv(df, name, OPENBB_DATA_DIR)


def _write_macro_data() -> None:
    """Write mock macroeconomic CSVs (CPI, unemployment, GDP, treasury rates)."""
    months = 48
    dates = _monthly_series(months)

    # CPI / unemployment come as decimals (0.031 = 3.1%) per generate_report logic.
    cpi_series = {
        "us_cpi": (0.029, 0.033),  # 2.9% -> 3.3%
        "eu_cpi": (0.025, 0.027),
        "spain_cpi": (0.031, 0.035),
    }
    for name, (start, end) in cpi_series.items():
        df = pd.DataFrame({"date": dates, "value": _trend(start, end, months)})
        save_to_csv(df, name, OPENBB_DATA_DIR)

    unemployment_series = {
        "us_unemployment": (0.037, 0.040),
        "eu_unemployment": (0.065, 0.060),
        "spain_unemployment": (0.125, 0.112),
    }
    for name, (start, end) in unemployment_series.items():
        df = pd.DataFrame({"date": dates, "value": _trend(start, end, months)})
        save_to_csv(df, name, OPENBB_DATA_DIR)

    # GDP (nominal + real) - quarterly, absolute values in billions.
    quarters = 24
    q_dates = _monthly_series(quarters)[::3] if quarters > 1 else _monthly_series(quarters)
    # Keep quarterly spacing distinct from monthly: recompute quarterly dates.
    end = datetime.now(timezone.utc).replace(day=1)
    q_dates = []
    for i in range(quarters - 1, -1, -1):
        d = end - timedelta(days=90 * i)
        q_dates.append(d.strftime("%Y-%m-%d"))
    gdp_series = {
        "us_gdp": (27000.0, 28200.0),
        "us_gdp_real": (23000.0, 23900.0),
    }
    for name, (start, end_val) in gdp_series.items():
        df = pd.DataFrame({"date": q_dates, "value": _trend(start, end_val, quarters)})
        save_to_csv(df, name, OPENBB_DATA_DIR)

    # GDP YoY - single value as a decimal (0.025 = 2.5%).
    for name, val in {
        "us_gdp_yoy": 0.025,
        "eu_gdp_yoy": 0.008,
        "spain_gdp_yoy": 0.021,
    }.items():
        df = pd.DataFrame({"gdp_yoy": [val]})
        save_to_csv(df, name, OPENBB_DATA_DIR)

    # US Treasury rates - treasury rates come as decimals (0.0445 = 4.45%).
    treasury_dates = _date_series(400)  # _date_series already uses tz-aware now
    treasury_df = pd.DataFrame(
        {
            "date": treasury_dates,
            "year_10": _trend(0.038, 0.0445, len(treasury_dates)),
        }
    )
    save_to_csv(treasury_df, "us_treasury_rates", OPENBB_DATA_DIR)


def _obs_history(value_now: float, value_year_ago: float, value_month_ago: float) -> list[dict]:
    """Build a sorted observation history for a single series.

    generate_report expects observations sorted oldest-first, each with
    ``time`` (date string) and ``value`` keys, and needs at least two points
    to compute 1-month and 1-year changes. Dates are relative to the current
    runtime date so the spread chart's last-365-days filter keeps them.
    """
    today = datetime.now(timezone.utc)
    return [
        {"time": (today - timedelta(days=360)).strftime("%Y-%m-%d"), "value": value_year_ago},
        {"time": (today - timedelta(days=30)).strftime("%Y-%m-%d"), "value": value_month_ago},
        {"time": today.strftime("%Y-%m-%d"), "value": value_now},
    ]


def _write_custom_data() -> None:
    """Write mock JSON datasets into the custom data directory."""
    # Euribor rates
    euribor = {
        "rates": {"EURIBOR_12M": 3.95},
        "history": {
            "EURIBOR_12M": _obs_history(
                value_now=3.95, value_year_ago=3.80, value_month_ago=3.90
            ),
        },
    }
    save_to_json(euribor, "euribor", CUSTOM_DATA_DIR)

    # ECB reference rates (ESTR is used for the Euribor-€STR spread)
    ecb_ref = {
        "rates": {"ESTR": 3.75, "MRO": 4.25, "DFR": 4.00},
        "history": {
            "ESTR": _obs_history(3.75, 3.60, 3.70),
            "MRO": _obs_history(4.25, 4.00, 4.15),
            "DFR": _obs_history(4.00, 3.75, 3.90),
        },
    }
    save_to_json(ecb_ref, "ecb_reference_rates", CUSTOM_DATA_DIR)

    # ECB yield curve
    ecb_yields = {
        "yields": {"1Y": 3.40, "10Y": 3.05},
        "history": {
            "1Y": _obs_history(3.40, 3.10, 3.30),
            "10Y": _obs_history(3.05, 2.70, 2.95),
        },
    }
    save_to_json(ecb_yields, "ecb_yield_curve", CUSTOM_DATA_DIR)

    # Spain-Germany 10Y bond spread
    bond_spreads = {
        "spread": 0.72,
        "history": {
            "spread": _obs_history(0.72, 0.95, 0.78),
        },
    }
    save_to_json(bond_spreads, "bond_spreads", CUSTOM_DATA_DIR)

    # Spanish real estate indicators
    real_estate = {
        "indicators": {
            "house_price_index": {
                "value": 1125.4,
                "previous": 1100.2,
                "change_1m": 2.1,
                "change_1y": 8.3,
                "unit": "index",
                "description": "House Price Index (IPV) - residential property prices",
                "source": "INE (National Statistics Institute)",
            },
            "avg_mortgage_rate": {
                "value": 3.15,
                "previous": 3.30,
                "change_1m": -4.5,
                "change_1y": -8.2,
                "unit": "",
                "description": "Average interest rate for new mortgage loans in Spain",
                "source": "INE (National Statistics Institute)",
            },
            "new_mortgage_loans_count": {
                "value": 45200,
                "previous": 42100,
                "change_1m": 7.4,
                "change_1y": 15.1,
                "unit": "loans",
                "description": "Number of new mortgage loans signed in Spain",
                "source": "INE (National Statistics Institute)",
            },
            "new_mortgage_loans_value": {
                "value": 8950.0,
                "previous": 8400.0,
                "change_1m": 6.5,
                "change_1y": 12.0,
                "unit": "M EUR",
                "description": "Total value of new mortgage loans in Spain",
                "source": "INE (National Statistics Institute)",
            },
            "fixed_vs_variable_rate_share": {
                "value": 68.5,
                "previous": 65.0,
                "change_1m": 5.4,
                "change_1y": 9.8,
                "unit": "%",
                "description": "Share of new mortgages with fixed vs variable rate",
                "source": "INE (National Statistics Institute)",
            },
            "mortgage_approval_time": {
                "value": 24,
                "previous": 26,
                "change_1m": -7.7,
                "change_1y": -12.1,
                "unit": "months",
                "description": "Average mortgage term in Spain",
                "source": "INE (National Statistics Institute)",
            },
        }
    }
    save_to_json(real_estate, "spanish_real_estate", CUSTOM_DATA_DIR)


def generate_test_report(report_type: str = "daily", output_format: str = "html") -> None:
    """Write mock data to the local cache and generate a report from it.

    No network calls are made; the report is produced entirely from the
    deterministic mock data written here.
    """
    logger.info("=" * 60)
    logger.info("Generating LOCAL TEST report from mock data (no network)")
    logger.info("=" * 60)

    logger.info("Writing mock market data...")
    _write_market_data()

    logger.info("Writing mock macro data...")
    _write_macro_data()

    logger.info("Writing mock custom data...")
    _write_custom_data()

    logger.info("Generating report from mock data...")
    generate_report(report_type=report_type, output_format=output_format, publish=False)

    logger.info("=" * 60)
    logger.info("Local test report generation completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a local test report from deterministic mock data"
    )
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
        default="html",
        choices=["html", "pdf", "both"],
        help="Output format (default: html)",
    )
    args = parser.parse_args()

    generate_test_report(report_type=args.type, output_format=args.output)
