"""Excel file handling utilities for AD Role Mapping Tool."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)

REQUIRED_SHEETS = ["Users", "Groups", "User_Groups", "Group_Groups"]


class ExcelHandler:
    """Handles Excel file operations for AD role mapping."""

    def __init__(self, input_file: Union[str, Path]):
        """Initialize ExcelHandler with input file path.

        Args:
            input_file: Path to the input Excel file.
        """
        self.input_file = Path(input_file)
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

    def read_sheets(self) -> Dict[str, DataFrame]:
        """Read all required sheets from the Excel file.

        Returns:
            Dict[str, DataFrame]: Dictionary of sheet names to DataFrames.

        Raises:
            ValueError: If required sheets are missing.
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

        Args:
            output_file: Path to the output Excel file.
            sheets: Dictionary of sheet names to DataFrames for required sheets.
            additional_sheets: Optional dictionary of additional sheets to write.

        Raises:
            ValueError: If required sheets are missing.
        """
        output_file = Path(output_file)
        missing_sheets = set(REQUIRED_SHEETS) - set(sheets.keys())
        if missing_sheets:
            raise ValueError(f"Missing required sheets: {missing_sheets}")

        try:
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

        Args:
            sheet_name: Name of the sheet being validated.
            df: DataFrame containing sheet data.

        Returns:
            List[str]: List of validation errors, empty if validation passes.
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