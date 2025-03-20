"""Excel file handling utilities for AD Role Mapping Tool.

This module provides functionality for reading, writing, and validating Excel files
used in the AD Role Mapping Tool. It handles:
- Reading input Excel files with AD data
- Validating sheet presence and schema requirements
- Writing output Excel files with role mappings

The module requires specific sheets to be present in the Excel files:
- Users: Contains AD user information
- Groups: Contains AD group information
- User_Groups: Contains user-group membership relationships
- Group_Groups: Contains group hierarchy relationships

Example:
    handler = ExcelHandler()
    sheets = handler.read_sheets("input.xlsx")

    # Process the data...

    handler.write_output(
        "output.xlsx",
        sheets,
        additional_sheets={"Roles": roles_df}
    )
"""

import logging
from pathlib import Path
from typing import Dict, List, Set, Union

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelHandler:
    """Handle Excel file operations."""

    def __init__(self):
        """Initialize ExcelHandler."""
        self.required_sheets: Set[str] = {"Users", "Groups"}

    def read_sheets(self, input_file: Union[str, Path]) -> Dict[str, pd.DataFrame]:
        """Read all sheets from an Excel file.

        Args:
            input_file: Path to the Excel file to read

        Returns:
            Dict mapping sheet names to DataFrames

        Raises:
            FileNotFoundError: If input_file doesn't exist
            ValueError: If required sheets are missing or empty
        """
        # Ensure input file exists
        if not Path(input_file).exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Read all sheets
        sheets = pd.read_excel(input_file, sheet_name=None)

        # Check for required sheets
        missing_sheets = self.required_sheets - set(sheets.keys())
        if missing_sheets:
            raise ValueError(f"Missing required sheet(s): {missing_sheets}")

        # Check for empty required sheets
        for sheet_name in self.required_sheets:
            if sheets[sheet_name].empty:
                raise ValueError(f"Required sheet '{sheet_name}' is empty")

        return sheets

    def write_output(
        self,
        output_file: Union[str, Path],
        sheets: Dict[str, pd.DataFrame],
    ) -> None:
        """Write data to Excel file.

        Args:
            output_file: Path where the output Excel file should be written
            sheets: Dictionary containing all sheets to write

        Raises:
            ValueError: If required sheets are missing or empty
            PermissionError: If unable to write to output file
        """
        output_file = Path(output_file)

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Check for required sheets
        missing_sheets = self.required_sheets - set(sheets.keys())
        if missing_sheets:
            raise ValueError(f"Missing required sheet(s): {missing_sheets}")

        # Define sheet order
        sheet_order = [
            "Users",
            "Groups",
            "Roles",  # New sheet
            "User_Groups",
            "Group_Groups",
            "Role_Groups",  # New sheet
            "User_Roles",  # New sheet
            "Group_Roles",  # New sheet
        ]

        try:
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # Write sheets in order
                for sheet_name in sheet_order:
                    if sheet_name in sheets:
                        sheets[sheet_name].to_excel(
                            writer, sheet_name=sheet_name, index=False
                        )

        except PermissionError:
            raise PermissionError(f"Unable to write to output file: {output_file}")
        except Exception as e:
            raise ValueError(f"Error writing output file: {e}")

    def validate_sheet_schema(self, sheet_name: str, df: pd.DataFrame) -> List[str]:
        """Validate sheet data against schema requirements.

        Performs basic schema validation for each sheet, checking for:
        1. Sheet emptiness
        2. Presence of required columns
        3. Sheet-specific requirements

        Args:
            sheet_name: Name of the sheet being validated (must be one of REQUIRED_SHEETS)
            df: DataFrame containing the sheet's data to validate

        Returns:
            List[str]: List of validation error messages. Empty list if validation passes.

        Example:
            >>> users_df = pd.DataFrame({
            ...     "username": ["user1"],  # Missing required user_id and email
            ... })
            >>> errors = handler.validate_sheet_schema("Users", users_df)
            >>> print(errors)
            ['Missing required columns in Users sheet: {'user_id', 'email'}']

        Note:
            Sheet-specific requirements:
            - Users: Must have user_id, username, and email columns
            - Groups: Must have group_id and group_name columns
            - User_Groups: Must have user_id and group_id columns
            - Group_Groups: Must have parent_group_id and child_group_id columns
        """
        errors = []

        # Common validation for all sheets
        if df.empty:
            errors.append(f"Sheet '{sheet_name}' is empty")

        # Sheet-specific validation
        if sheet_name == "Users":
            required_cols = ["user_id", "username", "email"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(
                    f"Missing required columns in Users sheet: {missing_cols}"
                )

        elif sheet_name == "Groups":
            required_cols = ["group_id", "group_name"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(
                    f"Missing required columns in Groups sheet: {missing_cols}"
                )

        elif sheet_name == "User_Groups":
            required_cols = ["user_id", "group_id"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(
                    f"Missing required columns in User_Groups sheet: {missing_cols}"
                )

        elif sheet_name == "Group_Groups":
            required_cols = ["source_group_id", "destination_group_id"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(
                    f"Missing required columns in Group_Groups sheet: {missing_cols}"
                )

        return errors
