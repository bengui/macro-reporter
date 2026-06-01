"""Caching utilities for macro_reporter."""

import json
from pathlib import Path
from typing import Any, Union

import pandas as pd


DATA_DIR = Path(__file__).parent.parent.parent / "data"
OPENBB_DATA_DIR = DATA_DIR / "openbb_data"
CUSTOM_DATA_DIR = DATA_DIR / "custom_data"


def ensure_directory(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def save_to_csv(
    data: pd.DataFrame,
    filename: str,
    directory: Union[Path, str] = OPENBB_DATA_DIR,
    index: bool = False,
) -> Path:
    """
    Save DataFrame to CSV file.
    
    Args:
        data: DataFrame to save
        filename: Filename (without extension)
        directory: Directory to save file
        index: Whether to save index
    
    Returns:
        Path to saved file
    """
    directory = Path(directory)
    ensure_directory(directory)
    filepath = directory / f"{filename}.csv"
    data.to_csv(filepath, index=index)
    return filepath


def load_from_csv(
    filename: str,
    directory: Union[Path, str] = OPENBB_DATA_DIR,
    **kwargs,
) -> pd.DataFrame:
    """
    Load DataFrame from CSV file.
    
    Args:
        filename: Filename (without extension)
        directory: Directory containing file
        **kwargs: Additional arguments to pass to pd.read_csv
    
    Returns:
        Loaded DataFrame
    """
    directory = Path(directory)
    filepath = directory / f"{filename}.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    return pd.read_csv(filepath, **kwargs)


def save_to_json(
    data: Any,
    filename: str,
    directory: Union[Path, str] = CUSTOM_DATA_DIR,
    indent: int = 2,
) -> Path:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save (dict, list, etc.)
        filename: Filename (without extension)
        directory: Directory to save file
        indent: JSON indentation
    
    Returns:
        Path to saved file
    """
    directory = Path(directory)
    ensure_directory(directory)
    filepath = directory / f"{filename}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)
    return filepath


def load_from_json(
    filename: str,
    directory: Union[Path, str] = CUSTOM_DATA_DIR,
) -> Any:
    """
    Load data from JSON file.
    
    Args:
        filename: Filename (without extension)
        directory: Directory containing file
    
    Returns:
        Loaded data
    """
    directory = Path(directory)
    filepath = directory / f"{filename}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_cache(directory: Union[Path, str] = DATA_DIR) -> int:
    """
    Clear all cached data files recursively.
    
    Args:
        directory: Directory to clear (default: DATA_DIR)
    
    Returns:
        Number of files deleted
    """
    from itertools import chain
    directory = Path(directory)
    count = 0
    # Clear files recursively in all subdirectories
    # Use chain to combine multiple rglob generators
    for filepath in chain(
        directory.rglob("*.csv"),
        directory.rglob("*.json"),
        directory.rglob("*.pdf"),
        directory.rglob("*.html")
    ):
        filepath.unlink()
        count += 1
    return count


def clear_all_data() -> int:
    """
    Clear all data files from the entire data directory.
    
    This removes all cached CSV, JSON, PDF, and HTML files recursively
    from the data/ directory and its subdirectories (openbb_data/, custom_data/, reports/).
    
    Returns:
        Number of files deleted
    """
    return clear_cache(DATA_DIR)
