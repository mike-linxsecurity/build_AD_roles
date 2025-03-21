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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import pandas as pd

from src.utils.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class ExcelHandler:
    """Handles Excel file operations."""

    def __init__(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize the Excel handler.

        Args:
            file_path: Optional path to the Excel file
        """
        self.file_path = Path(file_path) if file_path else None
        self.required_sheets = {
            "Users",
            "Groups",
            "Roles",
            "User_Groups",
            "Group_Groups",
            "User_Roles",
            "Group_Roles",
        }
        self.field_mappings = {
            "Group_Groups": {
                "source_group_id": "parent_group_id",
                "destination_group_id": "child_group_id",
            }
        }
        self.schema_validator = SchemaValidator()

    def load_sheets(self) -> Dict[str, pd.DataFrame]:
        """Load all sheets from the Excel file.

        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        sheets = {}
        with pd.ExcelFile(self.file_path) as excel_file:
            sheet_names = excel_file.sheet_names
            logger.info(f"Found sheets: {sheet_names}")
            for sheet_name in sheet_names:
                sheets[sheet_name] = pd.read_excel(excel_file, sheet_name=sheet_name)
        return sheets

    def save_sheets(self, data: Dict[str, pd.DataFrame], output_file: str) -> None:
        """Save multiple DataFrames to an Excel file with population rules applied."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Apply population rules
        processed_data = {}

        # Process Users sheet first
        if "Users" in data:
            processed_data["Users"] = self._populate_user_fields(data["Users"])

        # Process Groups sheet
        if "Groups" in data:
            processed_data["Groups"] = self._populate_group_fields(data["Groups"])

        # Process Roles sheet
        if "Roles" in data:
            processed_data["Roles"] = self._populate_role_fields(data["Roles"])

        # Process relationship sheets
        for sheet_name in ["User_Groups", "Group_Groups", "User_Roles", "Group_Roles"]:
            if sheet_name in data:
                processed_data[sheet_name] = self._populate_relationship_fields(
                    data[sheet_name],
                    processed_data.get("Users", pd.DataFrame()),
                    processed_data.get("Groups", pd.DataFrame()),
                )

        # Define the order of sheets
        sheet_order = [
            "Users",
            "Groups",
            "Roles",
            "User_Groups",
            "Group_Groups",
            "User_Roles",
            "Group_Roles",
        ]

        # Create a writer object
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Write each sheet in order
            for sheet_name in sheet_order:
                df = processed_data.get(sheet_name, pd.DataFrame())

                # Ensure required columns exist
                required_columns = self._get_required_columns(sheet_name)
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = ""

                # Convert all columns to strings
                df = df.astype(str)

                # Write the sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.debug(
                    f"Wrote sheet {sheet_name} with {len(df)} rows and columns: {list(df.columns)}"
                )

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
        logger.debug(f"Reading Excel file: {input_file}")

        # Ensure input file exists
        if not Path(input_file).exists():
            logger.error(f"Input file not found: {input_file}")
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Read all sheets
        sheets = pd.read_excel(input_file, sheet_name=None, index_col=None)
        logger.info(f"Found sheets: {list(sheets.keys())}")

        # Initialize processed sheets with empty DataFrames for all expected sheets
        processed_sheets = {}
        all_expected_sheets = {
            "Users",
            "Groups",
            "Roles",
            "User_Groups",
            "Group_Groups",
            "User_Roles",
            "Group_Roles",
        }

        for sheet_name in all_expected_sheets:
            required_cols = self._get_required_columns(sheet_name)
            processed_sheets[sheet_name] = pd.DataFrame(columns=required_cols)

        # Process existing sheets
        for sheet_name, df in sheets.items():
            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Sheet {sheet_name} is not a DataFrame, skipping")
                continue

            logger.debug(f"Sheet {sheet_name} shape: {df.shape}")
            logger.debug(f"Sheet {sheet_name} columns: {df.columns.tolist()}")
            logger.debug(f"Sheet {sheet_name} first few rows:\n{df.head()}")

            # Skip empty DataFrames
            if df.empty:
                logger.debug(
                    f"Sheet {sheet_name} is empty, using default empty DataFrame"
                )
                continue

            # Apply field mappings if they exist for this sheet
            if sheet_name in self.field_mappings:
                logger.debug(f"Applying field mappings for {sheet_name}")
                for source_field, target_field in self.field_mappings[
                    sheet_name
                ].items():
                    if source_field in df.columns:
                        logger.debug(f"Mapping {source_field} to {target_field}")
                        df[target_field] = df[source_field]

            # Only include columns that are in the required columns list
            required_cols = self._get_required_columns(sheet_name)
            if required_cols:
                # Ensure all required columns exist
                missing_cols = set(required_cols) - set(df.columns)
                if missing_cols:
                    logger.debug(f"Sheet {sheet_name} missing columns: {missing_cols}")
                    for col in missing_cols:
                        df[col] = None
                # Select only required columns
                df = df[required_cols]

            # Skip if DataFrame is empty after processing
            if df.empty:
                logger.debug(
                    f"Sheet {sheet_name} is empty after processing, using default empty DataFrame"
                )
                continue

            processed_sheets[sheet_name] = df

        # Log final processed sheets
        logger.debug("Final processed sheets:")
        for sheet_name, df in processed_sheets.items():
            logger.debug(
                f"{sheet_name}: shape={df.shape}, columns={df.columns.tolist()}"
            )

        return processed_sheets

    def write_output(
        self,
        sheets: Dict[str, pd.DataFrame],
        output_file: Union[str, Path],
    ) -> None:
        """Write data to Excel file.

        Args:
            sheets: Dictionary containing all sheets to write
            output_file: Path where the output Excel file should be written

        Raises:
            ValueError: If required sheets are missing or empty
            PermissionError: If unable to write to output file
        """
        # Check for required sheets
        missing_sheets = self.required_sheets - set(sheets.keys())
        if missing_sheets:
            raise ValueError(f"Missing required sheet(s): {missing_sheets}")

        # Ensure all sheets are DataFrames with required columns
        for sheet_name, df in sheets.items():
            if not isinstance(df, pd.DataFrame):
                required_cols = self._get_required_columns(sheet_name)
                sheets[sheet_name] = pd.DataFrame(columns=required_cols)
            elif df.empty:
                required_cols = self._get_required_columns(sheet_name)
                sheets[sheet_name] = pd.DataFrame(columns=required_cols)

        try:
            # Define sheet order
            sheet_order = [
                "Users",
                "Groups",
                "Roles",
                "User_Groups",
                "Group_Groups",
                "User_Roles",
                "Group_Roles",
            ]

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # Write sheets in order
                for sheet_name in sheet_order:
                    df = sheets.get(sheet_name)
                    if df is not None and isinstance(df, pd.DataFrame):
                        if df.empty:
                            # Create empty DataFrame with required columns
                            required_cols = self._get_required_columns(sheet_name)
                            empty_df = pd.DataFrame(columns=required_cols)
                            empty_df.to_excel(
                                writer, sheet_name=sheet_name, index=False
                            )
                        else:
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        # Create empty DataFrame with required columns
                        required_cols = self._get_required_columns(sheet_name)
                        empty_df = pd.DataFrame(columns=required_cols)
                        empty_df.to_excel(writer, sheet_name=sheet_name, index=False)
        except PermissionError:
            raise PermissionError(f"Unable to write to output file: {output_file}")
        except Exception as e:
            raise ValueError(f"Error writing output file: {e}")

    def _get_required_columns(self, sheet_name: str) -> List[str]:
        """Get required columns for a sheet.

        Args:
            sheet_name: Name of the sheet

        Returns:
            List of required column names
        """
        required_columns = {
            "Users": ["user_id", "username", "email"],
            "Groups": [
                "group_id",
                "group_name",
                "group_description",
                "MemberOf",
                "DistinguishedName",
            ],
            "Roles": ["role_id", "role_name", "description", "source"],
            "User_Groups": ["user_id", "group_id"],
            "Group_Groups": ["parent_group_id", "child_group_id"],
            "User_Roles": ["user_id", "role_id"],
            "Group_Roles": ["group_id", "role_id"],
        }
        return required_columns.get(sheet_name, [])

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
            # Apply field mappings before validation
            df = df.copy()
            if sheet_name in self.field_mappings:
                for source_field, target_field in self.field_mappings[
                    sheet_name
                ].items():
                    if source_field in df.columns:
                        df[target_field] = df[source_field]

            required_cols = ["parent_group_id", "child_group_id"]
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                errors.append(
                    f"Missing required columns in Group_Groups sheet: {missing_cols}"
                )

        return errors

    def _populate_user_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Populate user fields according to rules."""
        # Create a copy to avoid modifying the original
        df = df.copy()

        # Populate user_id from email or username if absent
        if "user_id" in df.columns:
            mask = df["user_id"].isna()
            if "email" in df.columns:
                df.loc[mask, "user_id"] = df.loc[mask, "email"]
            elif "username" in df.columns:
                df.loc[mask, "user_id"] = df.loc[mask, "username"]

        # Populate username from email if absent
        if "username" in df.columns and "email" in df.columns:
            mask = df["username"].isna()
            df.loc[mask, "username"] = df.loc[mask, "email"].apply(
                lambda x: x.split("@")[0] if pd.notna(x) and "@" in str(x) else x
            )

        # Populate full_name from first_name and last_name if absent
        if (
            "full_name" in df.columns
            and "first_name" in df.columns
            and "last_name" in df.columns
        ):
            mask = df["full_name"].isna()
            df.loc[mask, "full_name"] = df.loc[mask].apply(
                lambda row: f"{row['first_name']} {row['last_name']}"
                if pd.notna(row["first_name"]) and pd.notna(row["last_name"])
                else None,
                axis=1,
            )

        return df

    def _populate_group_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Populate group fields according to rules."""
        # Create a copy to avoid modifying the original
        df = df.copy()

        # Populate description from group_name if absent
        if "description" in df.columns and "group_name" in df.columns:
            mask = df["description"].isna() & df["group_name"].notna()
            df.loc[mask, "description"] = df.loc[mask, "group_name"]

        # Assign incrementing numbers for group_id if absent
        if "group_id" in df.columns:
            mask = df["group_id"].isna()
            if mask.any():
                next_id = 1
                for idx in df[mask].index:
                    while f"G{next_id}" in df["group_id"].values:
                        next_id += 1
                    df.loc[idx, "group_id"] = f"G{next_id}"
                    next_id += 1

        return df

    def _populate_role_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Populate role fields according to rules."""
        # Create a copy to avoid modifying the original
        df = df.copy()

        # Populate role_id from role_name if absent
        if "role_id" in df.columns and "role_name" in df.columns:
            mask = df["role_id"].isna() & df["role_name"].notna()
            df.loc[mask, "role_id"] = df.loc[mask, "role_name"]

        return df

    def _populate_relationship_fields(
        self, df: pd.DataFrame, users_df: pd.DataFrame, groups_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Populate relationship fields according to rules."""
        # Create a copy to avoid modifying the original
        df = df.copy()

        if "user_id" in df.columns:
            # Try to populate user_id from email or username
            mask = df["user_id"].isna()
            if mask.any():
                user_map = {}
                if "email" in users_df.columns:
                    user_map.update(
                        users_df[["email", "user_id"]]
                        .dropna()
                        .set_index("email")["user_id"]
                    )
                if "username" in users_df.columns:
                    user_map.update(
                        users_df[["username", "user_id"]]
                        .dropna()
                        .set_index("username")["user_id"]
                    )

                df.loc[mask, "user_id"] = df.loc[mask, "user_id"].map(user_map)

        if "group_id" in df.columns:
            # Try to populate group_id from group_name
            mask = df["group_id"].isna()
            if mask.any() and "group_name" in groups_df.columns:
                group_map = (
                    groups_df[["group_name", "group_id"]]
                    .dropna()
                    .set_index("group_name")["group_id"]
                )
                df.loc[mask, "group_id"] = df.loc[mask, "group_id"].map(group_map)

        return df

    def _validate_users_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate Users sheet data."""
        return self.schema_validator._validate_users_schema(df)

    def _validate_groups_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate Groups sheet data."""
        return self.schema_validator._validate_groups_schema(df)

    def _validate_roles_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate Roles sheet data."""
        return self.schema_validator._validate_roles_schema(df)

    def _validate_user_groups_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate User_Groups sheet data."""
        return self.schema_validator._validate_user_groups_schema(df)

    def _validate_group_groups_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate Group_Groups sheet data."""
        return self.schema_validator._validate_group_groups_schema(df)

    def _validate_user_roles_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate User_Roles sheet data."""
        return self.schema_validator._validate_user_roles_schema(df)

    def _validate_group_roles_sheet(self, df: pd.DataFrame) -> List[str]:
        """Validate Group_Roles sheet data."""
        return self.schema_validator._validate_group_roles_schema(df)

    def read_excel(self) -> Dict[str, pd.DataFrame]:
        """Read Excel file and return sheets as DataFrames."""
        if not self.file_path or not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")

        sheets = pd.read_excel(self.file_path, sheet_name=None)
        print(f"Found sheets: {list(sheets.keys())}")
        return sheets

    def write_excel(self, sheets: Dict[str, pd.DataFrame]) -> None:
        """Write DataFrames to Excel file.

        Args:
            sheets: Dictionary of sheet names and their DataFrames
        """
        if not self.file_path:
            raise ValueError("No output file path specified")

        with pd.ExcelWriter(self.file_path) as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    def validate_sheets(self, sheets: Dict[str, pd.DataFrame]) -> List[str]:
        """Validate all sheets against their schemas.

        Args:
            sheets: Dictionary of sheet names and their DataFrames

        Returns:
            List of validation errors
        """
        errors = []

        # Check for required sheets
        missing_sheets = self.schema_validator.required_sheets - set(sheets.keys())
        if missing_sheets:
            errors.append(f"Missing required sheets: {missing_sheets}")
            return errors

        # Validate each sheet
        for sheet_name, df in sheets.items():
            sheet_errors = self.schema_validator.validate_dataframe(df, sheet_name)
            if sheet_errors:
                errors.extend([f"{sheet_name}: {error}" for error in sheet_errors])

        # Validate relationships if all required sheets are present
        if not errors and all(
            sheet in sheets
            for sheet in ["Users", "Groups", "User_Groups", "Group_Groups"]
        ):
            relationship_errors = self.schema_validator.validate_relationships(
                users_df=sheets["Users"],
                groups_df=sheets["Groups"],
                user_groups_df=sheets["User_Groups"],
                group_groups_df=sheets["Group_Groups"],
            )
            errors.extend(relationship_errors)

        return errors
