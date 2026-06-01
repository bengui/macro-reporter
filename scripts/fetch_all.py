#!/usr/bin/env python3
"""Fetch all custom data sources."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.logging import setup_logging

# Import all fetch functions
from scripts.fetch_ecb import (
    fetch_euribor,
    fetch_ecb_yield_curve,
    fetch_ecb_reference_rates,
    fetch_ecb_exchange_rates,
    fetch_bond_spreads,
)
from scripts.fetch_gdelt import fetch_gdelt
from scripts.fetch_supply_chain import fetch_supply_chain
from scripts.fetch_ipos import fetch_ipos
from scripts.fetch_spanish_real_estate import fetch_spanish_real_estate

logger = setup_logging("fetch_all")


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
    fetch_bond_spreads()
    fetch_spanish_real_estate()

    # Other custom APIs
    fetch_gdelt()
    fetch_supply_chain()
    fetch_ipos()

    logger.info("=" * 60)
    logger.info("Custom API data fetch completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    fetch_all()
