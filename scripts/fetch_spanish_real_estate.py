#!/usr/bin/env python3
"""Fetch Spanish real estate and mortgage indicators from Bank of Spain and INE."""

import sys
from datetime import datetime
from pathlib import Path

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


def fetch_spanish_real_estate() -> None:
    """Fetch Spanish real estate and mortgage indicators from Bank of Spain and INE.
    
    Indicators:
    1. Average Mortgage Interest Rate - Bank of Spain
    2. New Mortgage Loans Granted - Bank of Spain  
    3. Mortgage Repayment Burden - Bank of Spain / INE
    4. Mortgage Default Rate - Bank of Spain
    5. House Price Index (IPV) - INE
    6. Fixed vs. Variable Rate Mortgage Share - Bank of Spain
    7. Mortgage Approval Time - Spanish Mortgage Association (AHE)
    8. Mortgage Early Repayments - Bank of Spain
    
    Note: Currently using mock data. Real data would require Bank of Spain API access.
    """
    logger.info("Fetching Spanish Real Estate data...")
    
    # Mock data for demonstration
    # In production, this would fetch from Bank of Spain API: https://www.bde.es/en/estadisticas/
    real_estate_data = {
        "fetch_date": datetime.now().isoformat(),
        "indicators": {
            "avg_mortgage_rate": {
                "value": 3.25,
                "previous": 3.10,
                "change_1m": ((3.25 - 3.10) / 3.10) * 100,
                "change_1y": 0.5,
                "unit": "%",
                "description": "Average interest rate for new mortgage loans in Spain",
                "source": "Bank of Spain (Banco de España)",
                "frequency": "Monthly"
            },
            "new_mortgage_loans_count": {
                "value": 35000,
                "previous": 32000,
                "change_1m": ((35000 - 32000) / 32000) * 100,
                "change_1y": 8.5,
                "unit": "loans",
                "description": "Number of new mortgage loans signed in Spain",
                "source": "Bank of Spain (Banco de España)",
                "frequency": "Monthly"
            },
            "new_mortgage_loans_value": {
                "value": 6500000000,
                "previous": 6000000000,
                "change_1m": ((6500000000 - 6000000000) / 6000000000) * 100,
                "change_1y": 12.0,
                "unit": "€",
                "description": "Total value of new mortgage loans signed in Spain",
                "source": "Bank of Spain (Banco de España)",
                "frequency": "Monthly"
            },
            "mortgage_repayment_burden": {
                "value": 28.5,
                "previous": 27.8,
                "change_1m": ((28.5 - 27.8) / 27.8) * 100,
                "change_1y": 3.2,
                "unit": "%",
                "description": "Average mortgage payment as percentage of household income",
                "source": "Bank of Spain / INE",
                "frequency": "Quarterly"
            },
            "mortgage_default_rate": {
                "value": 0.85,
                "previous": 0.82,
                "change_1m": ((0.85 - 0.82) / 0.82) * 100,
                "change_1y": -15.0,
                "unit": "%",
                "description": "Percentage of mortgage loans in arrears (90+ days late)",
                "source": "Bank of Spain (Banco de España)",
                "frequency": "Quarterly"
            },
            "house_price_index": {
                "value": 112.5,
                "previous": 110.8,
                "change_1m": ((112.5 - 110.8) / 110.8) * 100,
                "change_1y": 4.5,
                "unit": "index",
                "description": "House Price Index (IPV) - residential property prices",
                "source": "INE (National Statistics Institute)",
                "frequency": "Quarterly"
            },
            "fixed_vs_variable_rate_share": {
                "value": 65.0,
                "previous": 62.5,
                "change_1m": ((65.0 - 62.5) / 62.5) * 100,
                "change_1y": 10.0,
                "unit": "%",
                "description": "Percentage of new mortgages with fixed interest rates",
                "source": "Bank of Spain (Banco de España)",
                "frequency": "Monthly"
            },
            "mortgage_approval_time": {
                "value": 22,
                "previous": 20,
                "change_1m": ((22 - 20) / 20) * 100,
                "change_1y": -5.0,
                "unit": "days",
                "description": "Average time to approve a mortgage loan",
                "source": "Spanish Mortgage Association (AHE)",
                "frequency": "Quarterly"
            },
            "mortgage_early_repayments": {
                "value": 8500000000,
                "previous": 8000000000,
                "change_1m": ((8500000000 - 8000000000) / 8000000000) * 100,
                "change_1y": 18.0,
                "unit": "€",
                "description": "Volume of early mortgage repayments (refinancing activity)",
                "source": "Bank of Spain (Banco de España)",
                "frequency": "Quarterly"
            }
        },
        "source": "Bank of Spain, INE, AHE (mock data)",
        "note": "Real implementation would require API access to Bank of Spain statistical services"
    }
    
    save_to_json(real_estate_data, "spanish_real_estate", CUSTOM_DATA_DIR)
    logger.info("  Saved Spanish Real Estate data (mock)")


if __name__ == "__main__":
    fetch_spanish_real_estate()
