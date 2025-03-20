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
    """Parse command line arguments.
    
    Defines and processes command-line arguments for the AD Role Mapping Tool.
    Provides help text and validation for required and optional arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments with the following attributes:
            - input (str): Path to input Excel file
            - output (str): Path to output Excel file
            - builtin_groups (str): Path to builtin_groups.json (optional)
            - log_level (str): Logging level (optional)
    
    Example:
        >>> args = parse_args()
        >>> print(args.input)
        'ad_export.xlsx'
        >>> print(args.log_level)
        'INFO'
    
    Note:
        - The builtin_groups argument defaults to 'builtin_groups.json' in the script directory
        - The log_level argument accepts standard Python logging levels
    """
    parser = argparse.ArgumentParser(
        description="AD Role Mapping Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic usage:
    %(prog)s --input ad_export.xlsx --output role_mappings.xlsx

  With custom configuration:
    %(prog)s --input ad_export.xlsx --output role_mappings.xlsx \\
             --builtin-groups custom_groups.json --log-level DEBUG
        """
    )
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
    """Main entry point for the AD role mapping tool.
    
    Orchestrates the complete role mapping process:
    1. Loads environment variables and parses arguments
    2. Reads and validates input data
    3. Creates role mappings from AD groups
    4. Resolves role inheritance and assignments
    5. Writes results to output file
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    
    Environment Variables:
        LOG_LEVEL: Logging level to use if not specified in arguments
    
    Example:
        >>> sys.argv = ['AD_oracle.py', '--input', 'ad_export.xlsx',
        ...            '--output', 'role_mappings.xlsx']
        >>> exit_code = main()
        >>> print(exit_code)
        0
    
    Note:
        - Loads environment variables from .env file if present
        - Validates all input data before processing
        - Handles errors gracefully with appropriate logging
        - Creates all necessary output directories
    """
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