#!/usr/bin/env python3
"""Main script for AD role mapping tool.

This script processes AD data from Excel files and maps roles based on group
memberships.
"""

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Union

import pandas as pd

from src.process_input import process_input_file
from src.utils.excel_handler import ExcelHandler
from src.utils.role_mapper import RoleMapper
from src.utils.schema_validator import SchemaValidator

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class UserFriendlyFormatter(logging.Formatter):
    """Format log messages in a user-friendly way."""

    def format(self, record):
        """Format the log record."""
        if record.levelno == logging.INFO:
            return record.getMessage()
        return ""


def setup_logging(log_level: str):
    """Set up logging configuration."""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/ad_role_mapper.log"),
        ],
    )
    # Set log level for specific loggers
    logging.getLogger("src").setLevel(logging.INFO)
    logging.getLogger("src.utils").setLevel(logging.INFO)


def process_ad_data(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    builtin_groups_file: Union[str, Path],
) -> int:
    """Process AD data and create role mappings.

    Args:
        input_file: Path to the input Excel file containing AD data
        output_file: Path where the processed data will be saved
        builtin_groups_file: Path to JSON file containing builtin group definitions

    Returns:
        0 on success, 1 on failure
    """
    try:
        setup_logging(os.getenv("LOG_LEVEL", "INFO"))
        logger = logging.getLogger(__name__)

        logger.info("Processing input file: %s", input_file)

        # Process input file with builtin groups
        processed_data = process_input_file(input_file, builtin_groups_file)
        logger.debug("Processed data: %s", processed_data)

        # Validate output data
        if not isinstance(processed_data, dict):
            raise ValueError("Processed data must be a dictionary")
        if "Roles" not in processed_data:
            raise ValueError("Processed data must contain 'Roles' key")
        if not isinstance(processed_data["Roles"], pd.DataFrame):
            raise ValueError("Roles must be a DataFrame")
        if len(processed_data["Roles"]) == 0:
            raise ValueError("No roles were created from the input groups")

        # Write output
        excel_handler = ExcelHandler(input_file)
        excel_handler.save_sheets(processed_data, output_file)

        # Print summary
        users_count = (
            len(processed_data["Users"])
            if isinstance(processed_data["Users"], pd.DataFrame)
            else 0
        )
        groups_count = (
            len(processed_data["Groups"])
            if isinstance(processed_data["Groups"], pd.DataFrame)
            else 0
        )
        roles_count = (
            len(processed_data["Roles"])
            if isinstance(processed_data["Roles"], pd.DataFrame)
            else 0
        )
        group_roles_count = (
            len(processed_data["Group_Roles"])
            if isinstance(processed_data["Group_Roles"], pd.DataFrame)
            else 0
        )
        user_roles_count = (
            len(processed_data["User_Roles"])
            if isinstance(processed_data["User_Roles"], pd.DataFrame)
            else 0
        )

        print("\n✨ AD Role Mapping Complete!\n")
        print("📊 Summary:")
        print(f"  • Users processed: {users_count}")
        print(f"  • Groups processed: {groups_count}")
        print(f"  • Roles created: {roles_count}")
        print(f"  • Group-role mappings: {group_roles_count}")
        print(f"  • User-role mappings: {user_roles_count}\n")
        print(f"📁 Output file: {output_file}")

        return 0
    except Exception as e:
        logger.error(f"Error processing AD data: {e}")
        return 1


def process_directory(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    builtin_groups_file: Union[str, Path],
) -> int:
    """Process all Excel files in a directory.

    Args:
        input_dir: Directory containing input Excel files
        output_dir: Directory where output files will be saved
        builtin_groups_file: Path to JSON file containing builtin group definitions

    Returns:
        0 on success, 1 on failure
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    builtin_groups_file = Path(builtin_groups_file)

    # Ensure directories exist
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Check if builtin_groups.json exists
    if not builtin_groups_file.exists():
        print("❌ Required file src/builtin_groups.json not found.")
        return 1

    # Find Excel files in input directory
    excel_files = list(input_dir.glob("*.xlsx"))

    if not excel_files:
        print("❌ No Excel files found in input directory.")
        print("Please place your AD export files in the 'input' directory.")
        return 1

    # Process each Excel file
    for excel_file in excel_files:
        output_file = output_dir / f"processed_{excel_file.name}"
        print(f"\n🔄 Processing {excel_file.name}...")
        try:
            process_ad_data(str(excel_file), str(output_file), str(builtin_groups_file))
            print(f"✅ Output saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error processing {excel_file.name}:")
            print(f"  {str(e)}")
            print("\nTraceback:")
            traceback.print_exc()
            continue

    print("\n✅ Conversion completed successfully!")
    print("Check the 'output' directory for processed files.")
    return 0


def parse_args():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--input",
        type=Path,
        help="Path to input Excel file containing AD data or directory containing Excel files",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write output Excel file or directory for processed files",
    )

    parser.add_argument(
        "--builtin-groups",
        type=Path,
        default=Path(__file__).parent / "builtin_groups.json",
        help="Path to JSON file containing builtin group definitions",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Set logging level (default: from LOG_LEVEL env var or INFO)",
    )

    return parser.parse_args()


def main() -> int:
    """Main function to process AD data."""
    try:
        args = parse_args()
        setup_logging(args.log_level)

        # If input is a directory, process all Excel files
        if args.input and args.input.is_dir():
            if not args.output:
                args.output = Path("output")
            return process_directory(args.input, args.output, args.builtin_groups)

        # Otherwise process a single file
        if not args.input or not args.output:
            print(
                "❌ Both --input and --output arguments are required for single file processing"
            )
            return 1

        logger.info(f"Processing input file: {args.input}")
        return process_ad_data(args.input, args.output, args.builtin_groups)

    except Exception as e:
        logger.error(f"Error processing AD data: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
