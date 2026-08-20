"""Utility functions for macro_reporter."""

from .api_keys import get_api_key, load_api_keys, set_api_key
from .caching import load_from_csv, load_from_json, save_to_csv, save_to_json
from .formatting import format_date, format_number, format_percentage
from .logging import (
    get_logger,
    log_data_issue,
    log_data_loaded,
    log_invalid_data,
    log_missing_data,
    setup_logging,
)

__all__ = [
    "format_date",
    "format_number",
    "format_percentage",
    "get_api_key",
    "get_logger",
    "load_api_keys",
    "load_from_csv",
    "load_from_json",
    "log_data_issue",
    "log_data_loaded",
    "log_invalid_data",
    "log_missing_data",
    "save_to_csv",
    "save_to_json",
    "set_api_key",
    "setup_logging",
]
