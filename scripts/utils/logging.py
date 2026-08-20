"""Logging utilities for macro_reporter."""

import logging
import sys


def setup_logging(
    name: str = "macro_reporter",
    log_file: str | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        name: Logger name
        log_file: Optional path to log file
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter with more detail
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "macro_reporter") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_data_issue(logger: logging.Logger, data_source: str, issue_type: str, details: str = "", level: int = logging.WARNING) -> None:
    """
    Log a data issue with a standardized format for easy filtering.
    
    This function provides consistent logging for data-related issues,
    making it easy to search logs for missing or invalid data.
    
    Args:
        logger: The logger instance to use
        data_source: Name of the data source (e.g., 'us_cpi', 'sp500', 'ecb_yield_curve')
        issue_type: Type of issue ('missing_file', 'empty_data', 'missing_column', 
                     'invalid_value', 'nan_value', 'load_error')
        details: Additional details about the issue
        level: Logging level (default: WARNING)
    """
    message = f"[DATA_ISSUE] {data_source}: {issue_type}"
    if details:
        message += f" - {details}"
    logger.log(level, message)


def log_missing_data(logger: logging.Logger, data_source: str, context: str = "") -> None:
    """
    Log that data is missing.
    
    Args:
        logger: The logger instance to use
        data_source: Name of the missing data source
        context: Additional context about where the data was expected
    """
    message = f"[MISSING_DATA] {data_source}"
    if context:
        message += f" - {context}"
    logger.warning(message)


def log_invalid_data(logger: logging.Logger, data_source: str, reason: str, value: any = None) -> None:
    """
    Log that data is invalid.
    
    Args:
        logger: The logger instance to use
        data_source: Name of the data source
        reason: Reason why the data is invalid
        value: The invalid value (will be truncated if too long)
    """
    value_str = str(value)[:100] if value is not None else "None"
    logger.warning(f"[INVALID_DATA] {data_source}: {reason} (value: {value_str})")


def log_data_loaded(logger: logging.Logger, data_source: str, record_count: int = 0, columns: list = None) -> None:
    """
    Log that data was successfully loaded.
    
    Args:
        logger: The logger instance to use
        data_source: Name of the data source
        record_count: Number of records loaded
        columns: List of column names in the data
    """
    message = f"[DATA_LOADED] {data_source}"
    if record_count > 0:
        message += f" - {record_count} records"
    if columns:
        message += f" - columns: {', '.join(columns[:5])}"
        if len(columns) > 5:
            message += f" (and {len(columns) - 5} more)"
    logger.info(message)
