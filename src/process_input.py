#!/usr/bin/env python3
"""Process AD export file and generate role mappings.

This script reads an AD export Excel file from the input directory,
validates its contents, and generates role mappings in the output directory.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Union

import pandas as pd

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.excel_handler import ExcelHandler
from src.utils.schema_validator import SchemaValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def process_input_file(
    input_file: Union[str, Path], builtin_groups_file: Union[str, Path] = None
) -> Dict[str, pd.DataFrame]:
    """Process and validate input Excel file containing AD data.

    Args:
        input_file: Path to input Excel file
        builtin_groups_file: Path to builtin groups JSON file

    Returns:
        Dictionary containing DataFrames for each sheet

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If required sheets or columns are missing
        ValueError: If data validation fails
    """
    logger.debug(f"Processing input file: {input_file}")

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if builtin_groups_file and not os.path.exists(builtin_groups_file):
        raise FileNotFoundError(f"Builtin groups file not found: {builtin_groups_file}")

    # Use ExcelHandler to read sheets
    excel_handler = ExcelHandler(input_file)
    processed_data = excel_handler.read_sheets(input_file)
    logger.debug(f"Read sheets: {list(processed_data.keys())}")

    # Ensure all required sheets are present and are DataFrames
    required_sheets = {"Users", "Groups", "User_Groups", "Group_Groups"}
    for sheet_name in required_sheets:
        if sheet_name not in processed_data:
            raise ValueError(f"Required sheet '{sheet_name}' is missing")
        elif not isinstance(processed_data[sheet_name], pd.DataFrame):
            raise ValueError(f"Sheet '{sheet_name}' is not a DataFrame")

    # Create role mappings if builtin_groups_file is provided
    if builtin_groups_file:
        from src.utils.role_mapper import RoleMapper

        role_mapper = RoleMapper(str(builtin_groups_file))
        role_mappings = role_mapper.create_role_mappings(processed_data["Groups"])

        # Resolve group-role relationships
        group_roles_df = role_mapper.resolve_group_roles(
            roles_df=role_mappings["Roles"],
            group_groups_df=processed_data["Group_Groups"],
            groups_df=processed_data["Groups"],
            group_roles_df=role_mappings["Group_Roles"],
        )

        # Resolve user-role relationships
        user_roles_df = role_mapper.resolve_user_roles(
            user_groups_df=processed_data["User_Groups"], group_roles_df=group_roles_df
        )

        # Add role mappings to processed data
        processed_data["Roles"] = role_mappings["Roles"]
        processed_data["Group_Roles"] = group_roles_df
        processed_data["User_Roles"] = user_roles_df

    # Ensure all required fields are present in Users DataFrame
    if "Users" in processed_data:
        users_df = processed_data["Users"]
        if users_df.empty:
            raise ValueError("Users DataFrame is empty")
        # Add missing required fields with default values
        if "enabled" not in users_df.columns:
            users_df["enabled"] = "yes"
        if "created_at" not in users_df.columns:
            users_df["created_at"] = "2024-03-20T12:00:00Z"
        if "updated_at" not in users_df.columns:
            users_df["updated_at"] = "2024-03-20T12:00:00Z"
        if "last_login_at" not in users_df.columns:
            users_df["last_login_at"] = "2024-03-20T12:00:00Z"
        if "full_name" not in users_df.columns and (
            "first_name" not in users_df.columns or "last_name" not in users_df.columns
        ):
            users_df["full_name"] = users_df["username"].apply(lambda x: f"User {x}")

    # Ensure all required fields are present in Groups DataFrame
    if "Groups" in processed_data:
        groups_df = processed_data["Groups"]
        if groups_df.empty:
            raise ValueError("Groups DataFrame is empty")
        # Add missing required fields with default values
        if "description" not in groups_df.columns:
            groups_df["description"] = groups_df["group_name"].apply(
                lambda x: f"Group {x}"
            )

    # Validate data against schema
    validator = SchemaValidator()
    validation_errors = validator.validate_sheets(processed_data)
    if validation_errors:
        raise ValueError(f"Error validating input data: {'; '.join(validation_errors)}")

    logger.debug("Processed data validation complete")
    logger.debug("Final processed data:")
    for sheet_name, df in processed_data.items():
        logger.debug(f"{sheet_name}: shape={df.shape}, columns={df.columns.tolist()}")
        if not df.empty:
            logger.debug(f"{sheet_name} data:\n{df}")

    return processed_data


def main():
    """Main function to process AD export file."""
    try:
        # Get the input file
        input_dir = project_root / "input"
        excel_files = list(input_dir.glob("*.xlsx"))

        if not excel_files:
            logger.error("No Excel files found in input directory")
            sys.exit(1)

        input_file = excel_files[0]  # Process the first Excel file found
        logger.info(f"Processing input file: {input_file}")

        # Initialize handlers
        excel_handler = ExcelHandler(input_file)
        validator = SchemaValidator()

        # Read and validate sheets
        sheets = excel_handler.read_sheets()
        logger.info("Successfully read input sheets")

        # Validate each sheet's schema
        for sheet_name, df in sheets.items():
            errors = validator.validate_dataframe(df, sheet_name)
            if errors:
                logger.error(f"Validation errors in {sheet_name}:")
                for error in errors:
                    logger.error(f"  - {error}")
                sys.exit(1)

        # Validate relationships
        relationship_errors = validator.validate_relationships(
            sheets["Users"],
            sheets["Groups"],
            sheets["User_Groups"],
            sheets["Group_Groups"],
        )
        if relationship_errors:
            logger.error("Relationship validation errors:")
            for error in relationship_errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        # Create output directory if it doesn't exist
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)

        # Write output file with validated data
        output_file = output_dir / f"AD_Roles_{input_file.stem}.xlsx"
        excel_handler.write_output(output_file, sheets)
        logger.info(f"Successfully wrote output to: {output_file}")

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
