"""Formatting utilities for macro_reporter."""

from datetime import datetime
from typing import Any, Optional


def format_number(
    value: Optional[float],
    decimals: int = 2,
    thousands_sep: str = ",",
    decimal_sep: str = ".",
) -> str:
    """
    Format a number with decimal places and thousands separator.
    For numbers > 1 million, uses M notation (e.g., 1.23M).
    
    Args:
        value: Number to format
        decimals: Number of decimal places
        thousands_sep: Thousands separator
        decimal_sep: Decimal separator
    
    Returns:
        Formatted string, or "NA" if value is None
    """
    if value is None:
        return "NA"
    
    # Use M notation for numbers > 1 million
    if abs(value) >= 1_000_000:
        millions = value / 1_000_000
        # Limit to 2 decimal places for M notation
        formatted = f"{millions:.2f}".rstrip('0').rstrip('.') if decimals > 0 else f"{millions:.0f}"
        return f"{formatted}M"
    
    return f"{value:,.{decimals}f}".replace(",", "TEMP").replace(".", decimal_sep).replace("TEMP", thousands_sep)


def format_percentage(
    value: Optional[float],
    decimals: int = 2,
    show_sign: bool = True,
) -> str:
    """
    Format a percentage value.
    
    Args:
        value: Percentage value (e.g., 5.5 for 5.5%)
        decimals: Number of decimal places
        show_sign: Whether to show + sign for positive values
    
    Returns:
        Formatted string with % sign, or "NA" if value is None
    """
    if value is None:
        return "NA"
    if show_sign and value > 0:
        sign = "+"
    else:
        sign = ""
    return f"{sign}{value:.{decimals}f}%"


def format_date(
    date: Optional[Any] = None,
    format_str: str = "%Y-%m-%d",
) -> str:
    """
    Format a date.
    
    Args:
        date: Date to format (default: current date)
        format_str: strftime format string
    
    Returns:
        Formatted date string
    """
    if date is None:
        date = datetime.now()
    if isinstance(date, str):
        date = datetime.fromisoformat(date.replace("Z", "+00:00"))
    return date.strftime(format_str)


def format_change(
    old_value: float,
    new_value: float,
    decimals: int = 2,
) -> str:
    """
    Format a change between two values as percentage.
    
    Args:
        old_value: Old value
        new_value: New value
        decimals: Number of decimal places
    
    Returns:
        Formatted change string
    """
    if old_value == 0:
        return "N/A"
    change = (new_value - old_value) / old_value * 100
    return format_percentage(change, decimals)


def format_currency(
    value: float,
    currency: str = "USD",
    decimals: int = 2,
) -> str:
    """
    Format a currency value.
    
    Args:
        value: Amount
        currency: Currency symbol (e.g., "USD", "EUR")
        decimals: Number of decimal places
    
    Returns:
        Formatted currency string
    """
    return f"{currency} {format_number(value, decimals)}"


def get_traffic_light_signal(
    value: float,
    thresholds: dict[str, float],
) -> str:
    """
    Get traffic light signal based on value and thresholds.
    
    Args:
        value: Value to check
        thresholds: Dictionary with 'red' and 'yellow' keys
    
    Returns:
        Traffic light emoji: 🟢 (green), 🟡 (yellow), 🔴 (red)
    """
    if value >= thresholds.get("red", float("inf")):
        return "🔴"
    elif value >= thresholds.get("yellow", float("inf")):
        return "🟡"
    else:
        return "🟢"


def get_traffic_light_signal_higher_better(
    value: float,
    thresholds: dict[str, float],
) -> str:
    """
    Get traffic light signal for metrics where higher is better (e.g., GDP growth).

    Args:
        value: Value to check
        thresholds: Dictionary with 'red' and 'yellow' keys.
                   red is the lower threshold (values <= red are worst).
                   yellow is the middle threshold (values <= yellow are caution).

    Returns:
        Traffic light emoji: 🟢 (green), 🟡 (yellow), 🔴 (red)
    """
    if value >= thresholds.get("yellow", float("inf")):
        return "🟢"
    elif value >= thresholds.get("red", float("-inf")):
        return "🟡"
    else:
        return "🔴"
