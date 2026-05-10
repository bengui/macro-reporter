#!/usr/bin/env python3
"""
Main entry point for macro_reporter.

This script provides a unified interface to fetch data and generate reports.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.logging import setup_logging

logger = setup_logging("main")


def run_fetch_openbb() -> bool:
    """Run fetch_openbb.py script."""
    logger.info("Running fetch_openbb.py...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/fetch_openbb.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"fetch_openbb.py failed:\n{result.stderr}")
            return False
        logger.info("fetch_openbb.py completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running fetch_openbb.py: {e}")
        return False


def run_fetch_custom() -> bool:
    """Run fetch_custom.py script."""
    logger.info("Running fetch_custom.py...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/fetch_custom.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"fetch_custom.py failed:\n{result.stderr}")
            return False
        logger.info("fetch_custom.py completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running fetch_custom.py: {e}")
        return False


def run_generate_report(report_type: str = "daily", output_format: str = "both") -> bool:
    """Run generate_report.py script."""
    logger.info(f"Running generate_report.py (type={report_type}, format={output_format})...")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/generate_report.py",
                "--type", report_type,
                "--output", output_format,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"generate_report.py failed:\n{result.stderr}")
            return False
        logger.info("generate_report.py completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running generate_report.py: {e}")
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Macro Economic Financial Report Generator"
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fetch data, don't generate report",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Only generate report from cached data",
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
        default="both",
        choices=["html", "pdf", "both"],
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--custom",
        action="store_true",
        help="Include custom API data (Iteration 2)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Fetch all data (OpenBB + Custom) and generate report",
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Macro Economic Financial Report Generator")
    logger.info("=" * 60)
    
    # Determine what to run
    if args.generate_only:
        # Only generate report
        success = run_generate_report(args.type, args.output)
        sys.exit(0 if success else 1)
    
    if args.fetch_only:
        # Only fetch data
        success = run_fetch_openbb()
        if args.custom:
            success = run_fetch_custom() and success
        sys.exit(0 if success else 1)
    
    if args.full:
        # Fetch all and generate
        success = run_fetch_openbb()
        success = run_fetch_custom() and success
        success = run_generate_report(args.type, args.output) and success
        sys.exit(0 if success else 1)
    
    # Default: fetch OpenBB data and generate report
    success = run_fetch_openbb()
    if args.custom:
        success = run_fetch_custom() and success
    if success:
        success = run_generate_report(args.type, args.output)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
