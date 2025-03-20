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
    handler = ExcelHandler("input.xlsx")
    sheets = handler.read_sheets()
    
    # Process the data...
    
    handler.write_output(
        "output.xlsx",
        sheets,
        additional_sheets={"Roles": roles_df}
    )
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)

REQUIRED_SHEETS = ["Users", "Groups", "User_Groups", "Group_Groups"]


class ExcelHandler:
    """Handles Excel file operations for AD role mapping.
    
    This class provides methods for reading AD data from Excel files,
    validating the data against schema requirements, and writing processed
    data back to Excel files.
    
    The handler enforces the presence of required sheets and their schema
    requirements to ensure data consistency. It supports:
    - Reading multiple sheets from Excel files
    - Basic schema validation for each sheet
    - Writing data to new Excel files with additional sheets
    
    Attributes:
        input_file (Path): Path to the input Excel file
        REQUIRED_SHEETS (List[str]): List of sheets that must be present
    """

    def __init__(self, input_file: Union[str, Path]):
        """Initialize ExcelHandler with input file path.

        Args:
            input_file: Path to the input Excel file. Can be either a string path
                       or a Path object.

        Raises:
            FileNotFoundError: If the input file doesn't exist
            
        Example:
            >>> handler = ExcelHandler("data/ad_export.xlsx")
            >>> print(handler.input_file)
            PosixPath('data/ad_export.xlsx')
        """
        self.input_file = Path(input_file)
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

    def read_sheets(self) -> Dict[str, DataFrame]:
        """Read all required sheets from the Excel file.

        Reads and validates the presence of all required sheets from the input
        Excel file. The required sheets are defined in REQUIRED_SHEETS.

        Returns:
            Dict[str, DataFrame]: Dictionary mapping sheet names to their
                                corresponding pandas DataFrames.

        Raises:
            ValueError: If any required sheets are missing from the file
            pd.errors.EmptyDataError: If the Excel file is empty
            pd.errors.ParserError: If there are issues parsing the Excel file
            
        Example:
            >>> handler = ExcelHandler("data/ad_export.xlsx")
            >>> sheets = handler.read_sheets()
            >>> print(sheets.keys())
            dict_keys(['Users', 'Groups', 'User_Groups', 'Group_Groups'])
            >>> print(sheets['Users'].columns)
            Index(['user_id', 'username', 'email', ...])
        
        Note:
            - Only reads sheets listed in REQUIRED_SHEETS
            - Ignores any additional sheets in the file
            - Logs errors before re-raising them
        """
        try:
            sheets = pd.read_excel(self.input_file, sheet_name=None)
            missing_sheets = set(REQUIRED_SHEETS) - set(sheets.keys())
            if missing_sheets:
                raise ValueError(f"Missing required sheets: {missing_sheets}")
            return {name: df for name, df in sheets.items() if name in REQUIRED_SHEETS}
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            raise

    def write_output(
        self,
        output_file: Union[str, Path],
        sheets: Dict[str, DataFrame],
        additional_sheets: Optional[Dict[str, DataFrame]] = None,
    ) -> None:
        """Write data to Excel file.

        Writes the processed data to a new Excel file, including both required
        sheets and any additional sheets (like Roles, User_Roles, etc.).

        Args:
            output_file: Path where the output Excel file should be written
            sheets: Dictionary containing required sheets and their data
            additional_sheets: Optional dictionary containing additional sheets
                             to write (e.g., Roles, User_Roles, Group_Roles)

        Raises:
            ValueError: If any required sheets are missing from the sheets dict
            PermissionError: If the output location isn't writable
            Exception: For other IO or Excel writing errors
            
        Example:
            >>> handler = ExcelHandler("input.xlsx")
            >>> sheets = handler.read_sheets()
            >>> # Add Roles sheet
            >>> roles_df = pd.DataFrame({
            ...     "role_id": ["R1"],
            ...     "role_name": ["Admin"]
            ... })
            >>> handler.write_output(
            ...     "output.xlsx",
            ...     sheets,
            ...     additional_sheets={"Roles": roles_df}
            ... )
        
        Note:
            - Creates parent directories if they don't exist
            - Uses openpyxl engine for Excel writing
            - Writes sheets without row indices
            - Logs success or failure of the write operation
        """
        output_file = Path(output_file)
        missing_sheets = set(REQUIRED_SHEETS) - set(sheets.keys())
        if missing_sheets:
            raise ValueError(f"Missing required sheets: {missing_sheets}")

        try:
            # Create parent directories if they don't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # Write required sheets
                for sheet_name in REQUIRED_SHEETS:
                    sheets[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

                # Write additional sheets if provided
                if additional_sheets:
                    for sheet_name, df in additional_sheets.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            logger.info(f"Successfully wrote output to {output_file}")
        except Exception as e:
            logger.error(f"Error writing Excel file: {e}")
            raise

    def validate_sheet_schema(self, sheet_name: str, df: DataFrame) -> List[str]:
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
                errors.append(f"Missing required columns in Users sheet: {missing_cols}")
        
        elif sheet_name == "Groups":
            required_cols = ["group_id", "group_name"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(f"Missing required columns in Groups sheet: {missing_cols}")
        
        elif sheet_name == "User_Groups":
            required_cols = ["user_id", "group_id"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(f"Missing required columns in User_Groups sheet: {missing_cols}")
        
        elif sheet_name == "Group_Groups":
            required_cols = ["parent_group_id", "child_group_id"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(f"Missing required columns in Group_Groups sheet: {missing_cols}")
        
        return errors 