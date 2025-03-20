#!/usr/bin/env python3
"""AD Role Mapping Tool main script."""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from utils.excel_handler import ExcelHandler
from utils.role_mapper import RoleMapper
from utils.schema_validator import SchemaValidator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AD Role Mapping Tool")
    parser.add_argument(
        "--input",
        required=True,
        type=str,
        help="Path to input Excel file containing AD data"
    )
    parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Path to output Excel file for role mappings"
    )
    parser.add_argument(
        "--builtin-groups",
        type=str,
        default=str(Path(__file__).parent / "builtin_groups.json"),
        help="Path to builtin_groups.json configuration file"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level"
    )
    return parser.parse_args()


def main():
    """Main entry point for the AD role mapping tool."""
    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    args = parse_args()

    # Set log level from arguments or environment
    log_level = args.log_level or os.getenv("LOG_LEVEL", "INFO")
    logging.getLogger().setLevel(log_level)

    try:
        # Initialize handlers
        excel_handler = ExcelHandler(args.input)
        role_mapper = RoleMapper(args.builtin_groups)
        validator = SchemaValidator()

        # Read input data
        logger.info("Reading input Excel file...")
        sheets = excel_handler.read_sheets()

        # Validate input data
        logger.info("Validating input data...")
        for sheet_name, df in sheets.items():
            errors = validator.validate_dataframe(df, sheet_name)
            if errors:
                for error in errors:
                    logger.error(f"Validation error in {sheet_name}: {error}")
                sys.exit(1)

        # Validate relationships
        relationship_errors = validator.validate_relationships(
            sheets["Users"],
            sheets["Groups"],
            sheets["User_Groups"],
            sheets["Group_Groups"]
        )
        if relationship_errors:
            for error in relationship_errors:
                logger.error(f"Relationship validation error: {error}")
            sys.exit(1)

        # Create role mappings
        logger.info("Creating role mappings...")
        roles_df = role_mapper.create_role_mappings(sheets["Groups"])

        # Resolve group roles
        logger.info("Resolving group roles...")
        group_roles_df = role_mapper.resolve_group_roles(roles_df, sheets["Group_Groups"])

        # Resolve user roles
        logger.info("Resolving user roles...")
        user_roles_df = role_mapper.resolve_user_roles(sheets["User_Groups"], group_roles_df)

        # Prepare output
        output_sheets = {
            **sheets,  # Include original sheets
            "Roles": roles_df,
            "User_Roles": user_roles_df,
            "Group_Roles": group_roles_df
        }

        # Write output
        logger.info("Writing output Excel file...")
        excel_handler.write_output(args.output, sheets, {
            "Roles": roles_df,
            "User_Roles": user_roles_df,
            "Group_Roles": group_roles_df
        })

        logger.info("Role mapping completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Error during role mapping: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 