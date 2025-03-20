"""Schema validation utilities for AD Role Mapping Tool.

This module provides functionality for validating data against schema requirements.
It ensures that input data meets the required format and contains all necessary fields.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Union

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates data against schema requirements.

    This class provides methods for validating data against schema requirements,
    including field presence, data types, and relationships between entities.
    """

    def __init__(self):
        """Initialize SchemaValidator."""
        self.required_sheets = {"Users", "Groups", "Group_Groups"}

        self.optional_sheets = {"User_Groups", "Roles", "Role_Groups"}

        self.schema = {
            "Users": {
                "required_fields": ["user_id", "username", "email"],
                "field_types": {
                    "user_id": str,
                    "username": str,
                    "email": str,
                    "is_active": str,
                    "created_at": datetime,
                    "updated_at": datetime,
                    "last_login_at": datetime,
                },
                "field_mappings": {"is_active": "enabled"},
            },
            "Groups": {
                "required_fields": ["group_id", "group_name"],
                "field_types": {
                    "group_id": str,
                    "group_name": str,
                    "group_description": str,
                },
                "field_mappings": {"group_description": "description"},
            },
            "Group_Groups": {
                "required_fields": ["source_group_id", "destination_group_id"],
                "field_types": {"source_group_id": str, "destination_group_id": str},
            },
            "User_Groups": {
                "required_fields": ["user_id", "group_id"],
                "field_types": {"user_id": str, "group_id": str},
            },
            "Roles": {
                "required_fields": ["role_id", "role_name"],
                "field_types": {"role_id": str, "role_name": str, "description": str},
            },
            "Role_Groups": {
                "required_fields": ["group_id", "role_id"],
                "field_types": {"group_id": str, "role_id": str},
            },
        }

    def validate_sheets(self, sheets: Dict[str, DataFrame]) -> List[str]:
        """Validate all sheets against schema requirements.

        Args:
            sheets: Dictionary of sheet names to DataFrames

        Returns:
            List[str]: List of validation error messages
        """
        errors = []

        # Check required sheets
        missing_sheets = self.required_sheets - set(sheets.keys())
        if missing_sheets:
            errors.append(f"Missing required sheet(s): {missing_sheets}")
            return errors

        # Validate each sheet
        for sheet_name, df in sheets.items():
            if sheet_name in self.schema:
                sheet_errors = self.validate_dataframe(df, sheet_name)
                errors.extend(sheet_errors)

        # Validate relationships
        relationship_errors = self.validate_relationships(sheets)
        errors.extend(relationship_errors)

        return errors

    def validate_dataframe(self, df: DataFrame, sheet_name: str) -> List[str]:
        """Validate a DataFrame against schema requirements.

        Args:
            df: DataFrame to validate
            sheet_name: Name of the sheet being validated

        Returns:
            List[str]: List of validation error messages
        """
        errors = []

        # Skip validation for empty optional sheets
        if sheet_name in self.optional_sheets and df.empty:
            return errors

        # Check if sheet is required and empty
        if sheet_name in self.required_sheets and df.empty:
            errors.append(f"Required sheet {sheet_name} is empty")
            return errors

        # Check if sheet is known
        if sheet_name not in self.schema:
            errors.append(f"Unknown sheet: {sheet_name}")
            return errors

        # Get schema for this sheet
        sheet_schema = self.schema[sheet_name]

        # Create a copy of the DataFrame to avoid modifying the original
        df = df.copy()

        # Apply field mappings if any exist
        if "field_mappings" in sheet_schema:
            for source_field, target_field in sheet_schema["field_mappings"].items():
                if source_field in df.columns:
                    df[target_field] = df[source_field]

        # Check required fields
        required_fields = sheet_schema.get("required_fields", [])
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")

        # Check field types
        field_types = sheet_schema.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in df.columns:
                if expected_type == datetime:
                    try:
                        pd.to_datetime(df[field])
                    except Exception as e:
                        errors.append(f"Invalid datetime in field {field}: {e}")
                else:
                    if not all(
                        isinstance(val, expected_type) for val in df[field].dropna()
                    ):
                        errors.append(
                            f"Invalid type in field {field}, expected {expected_type.__name__}"
                        )

        return errors

    def validate_relationships(self, sheets: Dict[str, DataFrame]) -> List[str]:
        """Validate relationships between sheets.

        Args:
            sheets: Dictionary of sheet names to DataFrames

        Returns:
            List[str]: List of validation error messages
        """
        errors = []

        # Check required sheets
        missing_sheets = self.required_sheets - set(sheets.keys())
        if missing_sheets:
            errors.append(f"Missing required sheets: {missing_sheets}")
            return errors

        # Validate Group-Group relationships
        if "Group_Groups" in sheets and "Groups" in sheets:
            group_ids = set(sheets["Groups"]["group_id"])
            for _, row in sheets["Group_Groups"].iterrows():
                source_id = row["source_group_id"]
                dest_id = row["destination_group_id"]
                if source_id not in group_ids:
                    errors.append(
                        f"Invalid source_group_id in Group_Groups: {source_id}"
                    )
                if dest_id not in group_ids:
                    errors.append(
                        f"Invalid destination_group_id in Group_Groups: {dest_id}"
                    )

        # Validate User-Group relationships if present
        if "User_Groups" in sheets and not sheets["User_Groups"].empty:
            user_ids = set(sheets["Users"]["user_id"])
            group_ids = set(sheets["Groups"]["group_id"])
            for _, row in sheets["User_Groups"].iterrows():
                user_id = row["user_id"]
                group_id = row["group_id"]
                if user_id not in user_ids:
                    errors.append(f"Invalid user_id in User_Groups: {user_id}")
                if group_id not in group_ids:
                    errors.append(f"Invalid group_id in User_Groups: {group_id}")

        return errors
