#!/usr/bin/env python3
"""
Fetch all data and store it in a test folder for offline testing.

This script fetches real data from all sources (OpenBB, ECB, GDELT, etc.) and
stores it in a separate test data folder. This allows you to:
1. Fetch fresh data once
2. Commit the test data to git
3. Use it later in sandbox/local environments without API access
4. Test report generation with real data

Usage:
    python scripts/fetch_and_store_test_data.py
    
    # Or with custom test data directory
    python scripts/fetch_and_store_test_data.py --test-data-dir ./test_data_backup
    
    # To commit the data after fetching
    python scripts/fetch_and_store_test_data.py --commit
    
    # To fetch and commit in one step
    python scripts/fetch_and_store_test_data.py --commit
"""

import argparse
import os
import shutil
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.caching import (
    OPENBB_DATA_DIR,
    CUSTOM_DATA_DIR,
    DATA_DIR,
)
from scripts.utils.logging import setup_logging, log_data_loaded, log_data_issue, log_missing_data

logger = setup_logging("fetch_and_store_test_data")

# Default test data directory (relative to repo root)
DEFAULT_TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"


def fetch_all_data() -> None:
    """Fetch data from all sources."""
    logger.info("=" * 60)
    logger.info("Fetching all data from all sources")
    logger.info("=" * 60)
    
    # Import and run fetch scripts
    try:
        # Fetch OpenBB data
        logger.info("\nFetching OpenBB data...")
        from scripts.fetch_openbb import fetch_all as fetch_openbb_all
        fetch_openbb_all()
        logger.info("OpenBB data fetched successfully")
    except Exception as e:
        log_data_issue(logger, "openbb", "fetch_error", str(e))
    
    try:
        # Fetch custom data
        logger.info("\nFetching custom API data...")
        from scripts.fetch_all import main as fetch_all_custom
        fetch_all_custom()
        logger.info("Custom data fetched successfully")
    except Exception as e:
        log_data_issue(logger, "custom_data", "fetch_error", str(e))
    
    logger.info("\n" + "=" * 60)
    logger.info("All data fetched successfully")
    logger.info("=" * 60)


def copy_data_to_test_folder(test_data_dir: Path, source_dir: Path) -> int:
    """
    Copy all data files from source directory to test data directory.
    
    Args:
        test_data_dir: Destination test data directory
        source_dir: Source data directory
    
    Returns:
        Number of files copied
    """
    count = 0
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all CSV and JSON files
    for filepath in source_dir.rglob("*.csv"):
        relative_path = filepath.relative_to(source_dir)
        dest = test_data_dir / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, dest)
        logger.info(f"  Copied: {relative_path}")
        count += 1
    
    for filepath in source_dir.rglob("*.json"):
        relative_path = filepath.relative_to(source_dir)
        dest = test_data_dir / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, dest)
        logger.info(f"  Copied: {relative_path}")
        count += 1
    
    return count


def store_test_data(test_data_dir: Path = None) -> Path:
    """
    Copy all fetched data to a test data directory.
    
    Args:
        test_data_dir: Directory to store test data (default: ./test_data)
    
    Returns:
        Path to the test data directory
    """
    if test_data_dir is None:
        test_data_dir = DEFAULT_TEST_DATA_DIR
    
    test_data_dir = Path(test_data_dir)
    
    logger.info("=" * 60)
    logger.info(f"Storing test data in: {test_data_dir}")
    logger.info("=" * 60)
    
    # Clear existing test data
    if test_data_dir.exists():
        logger.info(f"Clearing existing test data from {test_data_dir}")
        shutil.rmtree(test_data_dir)
    
    # Copy OpenBB data
    logger.info("\nCopying OpenBB data...")
    openbb_count = copy_data_to_test_folder(test_data_dir / "openbb_data", OPENBB_DATA_DIR)
    log_data_loaded(logger, "openbb_test_data", openbb_count, [])
    
    # Copy custom data
    logger.info("\nCopying custom data...")
    custom_count = copy_data_to_test_folder(test_data_dir / "custom_data", CUSTOM_DATA_DIR)
    log_data_loaded(logger, "custom_test_data", custom_count, [])
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Test data stored successfully in: {test_data_dir}")
    logger.info(f"Total files: {openbb_count + custom_count}")
    logger.info("=" * 60)
    
    return test_data_dir


def commit_test_data(test_data_dir: Path = None, commit_message: str = None) -> bool:
    """
    Commit the test data to git.
    
    Args:
        test_data_dir: Directory containing test data
        commit_message: Custom commit message (default: auto-generated)
    
    Returns:
        True if commit was successful, False otherwise
    """
    if test_data_dir is None:
        test_data_dir = DEFAULT_TEST_DATA_DIR
    
    test_data_dir = Path(test_data_dir)
    
    if not test_data_dir.exists():
        log_missing_data(logger, str(test_data_dir), "Directory does not exist")
        return False
    
    # Generate commit message if not provided
    if commit_message is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Update test data - {timestamp}"
    
    logger.info("=" * 60)
    logger.info("Committing test data to git")
    logger.info("=" * 60)
    
    try:
        # Add test data directory to git
        repo_root = Path(__file__).parent.parent
        result = subprocess.run(
            ["git", "add", str(test_data_dir.relative_to(repo_root))],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Failed to add test data: {result.stderr}")
            return False
        
        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Failed to commit: {result.stderr}")
            return False
        
        logger.info(f"Test data committed successfully")
        logger.info(f"Commit message: {commit_message}")
        
        # Show the commit
        result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"Commit: {result.stdout.strip()}")
        
        return True
        
    except Exception as e:
        log_data_issue(logger, "git_commit", "commit_error", str(e))
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch all data and store it in a test folder for offline testing"
    )
    parser.add_argument(
        "--test-data-dir",
        type=str,
        default=None,
        help="Directory to store test data (default: ./test_data)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit the test data to git after storing",
    )
    parser.add_argument(
        "--commit-message",
        type=str,
        default=None,
        help="Custom commit message for the test data",
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fetch data, don't store in test folder",
    )
    args = parser.parse_args()
    
    # Convert test_data_dir to Path if provided
    test_data_dir = Path(args.test_data_dir) if args.test_data_dir else None
    
    # Step 1: Fetch all data
    fetch_all_data()
    
    if args.fetch_only:
        logger.info("\nFetch-only mode: skipping test data storage")
        return
    
    # Step 2: Store data in test folder
    stored_dir = store_test_data(test_data_dir)
    
    # Step 3: Optionally commit to git
    if args.commit:
        success = commit_test_data(test_data_dir, args.commit_message)
        if not success:
            logger.error("Failed to commit test data")
            sys.exit(1)


if __name__ == "__main__":
    main()
