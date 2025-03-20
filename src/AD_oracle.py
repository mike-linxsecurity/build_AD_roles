#!/usr/bin/env python3
"""AD Role Mapping Tool main script.

This script is the main entry point for the AD Role Mapping Tool. It orchestrates
the process of mapping Active Directory groups to roles and resolving role
assignments for users. The tool:

1. Reads AD data from an Excel file containing:
   - Users sheet: AD user information
   - Groups sheet: AD group information
   - User_Groups sheet: User-group memberships
   - Group_Groups sheet: Group hierarchy relationships

2. Validates the input data:
   - Checks for required sheets and columns
   - Validates data types and formats
   - Ensures relationship integrity

3. Maps AD groups to roles:
   - Uses builtin_groups.json to identify role-eligible groups
   - Creates role definitions from eligible groups
   - Resolves role inheritance through group hierarchies
   - Determines user role assignments

4. Outputs results to a new Excel file with additional sheets:
   - Roles: Mapped role definitions
   - User_Roles: User role assignments
   - Group_Roles: Group role assignments

Usage:
    python AD_oracle.py --input input.xlsx --output output.xlsx [options]

Environment Variables:
    LOG_LEVEL: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
              Default: INFO

Example:
    # Basic usage
    python AD_oracle.py --input ad_export.xlsx --output role_mappings.xlsx

    # With custom builtin groups and debug logging
    python AD_oracle.py \\
        --input ad_export.xlsx \\
        --output role_mappings.xlsx \\
        --builtin-groups custom_groups.json \\
        --log-level DEBUG
"""

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd

from .process_input import process_input_file
from .utils.excel_handler import ExcelHandler
from .utils.role_mapper import RoleMapper

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Create a custom formatter that only shows the message
class UserFriendlyFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            return record.getMessage()
        return ""


# Configure console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(UserFriendlyFormatter())
logger.addHandler(console_handler)


def setup_logging():
    """Configure logging with user-friendly formatting."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(UserFriendlyFormatter())
    logger.addHandler(console_handler)


def process_ad_data(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    builtin_groups_file: Union[str, Path],
) -> None:
    """Process AD data and create role mappings.

    Args:
        input_file: Path to the input Excel file containing AD data
        output_file: Path where the processed data will be saved
        builtin_groups_file: Path to the JSON file containing builtin group definitions
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    print(f"Processing input file: {input_file}")

    # Process input file
    processed_data = process_input_file(input_file)

    # Create role mapper instance
    role_mapper = RoleMapper(builtin_groups_file)

    # Create role mappings
    role_mappings = role_mapper.create_role_mappings(processed_data["Groups"])

    # Add role-related sheets to the output
    processed_data.update(role_mappings)

    # Write output
    excel_handler = ExcelHandler()
    excel_handler.write_output(output_file, processed_data)

    # Print summary
    users_count = len(processed_data["Users"])
    groups_count = len(processed_data["Groups"])
    roles_count = len(processed_data.get("Roles", []))
    role_groups_count = len(processed_data.get("Role_Groups", []))

    print("\n✨ AD Role Mapping Complete!\n")
    print("📊 Summary:")
    print(f"  • Users processed: {users_count}")
    print(f"  • Groups processed: {groups_count}")
    print(f"  • Roles created: {roles_count}")
    print(f"  • Role-Group mappings: {role_groups_count}\n")
    print(f"📁 Output file: {output_file}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to input Excel file containing AD data",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write output Excel file with role mappings",
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


def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        # Process AD data
        process_ad_data(args.input, args.output, args.builtin_groups)

        return 0

    except Exception as e:
        logger.error(f"Error processing AD data: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
