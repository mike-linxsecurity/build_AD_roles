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

    SCHEMAS = {
        "Users": {
            "required": True,
            "fields": {
                "user_id": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of user_id, username, or email must be present",
                    "population": "If absent, populate from email; if email absent, use username",
                },
                "username": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of user_id, username, or email must be present",
                    "population": "If absent, populate from email",
                },
                "email": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of user_id, username, or email must be present",
                },
                "full_name": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "Either full_name or (first_name + last_name) must be present",
                    "population": "Concatenate first_name and last_name if absent",
                },
                "first_name": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "Either full_name or (first_name + last_name) must be present",
                },
                "last_name": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "Either full_name or (first_name + last_name) must be present",
                },
                "enabled": {"type": "boolean", "required": True},
                "created_at": {
                    "type": "datetime",
                    "required": True,
                    "format": "ISO 8601",
                },
                "updated_at": {
                    "type": "datetime",
                    "required": True,
                    "format": "ISO 8601",
                },
                "last_login_at": {
                    "type": "datetime",
                    "required": True,
                    "format": "ISO 8601",
                },
            },
        },
        "Groups": {
            "required": True,
            "fields": {
                "group_id": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of group_id or group_name must be present",
                    "population": "If absent, assign an incrementing number",
                },
                "group_name": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of group_id or group_name must be present",
                },
                "description": {
                    "type": "string",
                    "required": True,
                    "population": "If absent, populate from group_name",
                },
            },
            "output_order": ["group_id", "group_name", "description"],
        },
        "Roles": {
            "required": True,
            "fields": {
                "role_id": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of role_id or role_name must be present",
                    "population": "If absent, use role_name",
                },
                "role_name": {
                    "type": "string",
                    "required": "conditional",
                    "condition": "At least one of role_id or role_name must be present",
                },
                "description": {"type": "string", "required": True},
            },
            "output_order": ["role_id", "role_name", "description"],
        },
        "User_Groups": {
            "required": True,
            "fields": {
                "user_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use user_id from Users tab; if absent, use email; if email absent, use username",
                },
                "group_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use group_id from Groups tab; if absent, use assigned number",
                },
            },
        },
        "Group_Groups": {
            "required": True,
            "fields": {
                "parent_group_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use group_id from Groups tab; if absent, use assigned number",
                },
                "child_group_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use group_id from Groups tab; if absent, use assigned number",
                },
            },
        },
        "User_Roles": {
            "required": True,
            "fields": {
                "user_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use user_id from Users tab; if absent, use email; if email absent, use username",
                },
                "role_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use role_id from Roles tab; if absent, use role_name",
                },
            },
        },
        "Group_Roles": {
            "required": True,
            "fields": {
                "group_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use group_id from Groups tab; if absent, use assigned number",
                },
                "role_id": {
                    "type": "string",
                    "required": True,
                    "population": "Use role_id from Roles tab; if absent, use role_name",
                },
            },
        },
    }

    def __init__(self):
        """Initialize SchemaValidator."""
        self.required_sheets = {
            "Users",
            "Groups",
            "User_Groups",
            "Group_Groups",
            "Roles",
            "User_Roles",
            "Group_Roles",
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
            if sheet_name in self.SCHEMAS:
                if not isinstance(df, pd.DataFrame):
                    errors.append(f"Sheet '{sheet_name}' is not a DataFrame")
                    continue
                sheet_errors = self.validate_dataframe(df, sheet_name)
                errors.extend(sheet_errors)

        # Validate relationships
        if all(
            sheet in sheets
            for sheet in ["Users", "Groups", "User_Groups", "Group_Groups"]
        ):
            if all(
                isinstance(sheets[sheet], pd.DataFrame)
                for sheet in ["Users", "Groups", "User_Groups", "Group_Groups"]
            ):
                relationship_errors = self.validate_relationships(
                    users_df=sheets["Users"],
                    groups_df=sheets["Groups"],
                    user_groups_df=sheets["User_Groups"],
                    group_groups_df=sheets["Group_Groups"],
                )
                errors.extend(relationship_errors)

        return errors

    def validate_dataframe(self, df: pd.DataFrame, schema: str) -> List[str]:
        """Validate a DataFrame against its schema requirements."""
        errors = []

        if df.empty:
            errors.append(f"DataFrame for {schema} is empty")
            return errors

        if schema == "Users":
            errors.extend(self._validate_users_schema(df))
        elif schema == "Groups":
            errors.extend(self._validate_groups_schema(df))
        elif schema == "Roles":
            errors.extend(self._validate_roles_schema(df))
        elif schema == "User_Groups":
            errors.extend(self._validate_user_groups_schema(df))
        elif schema == "Group_Groups":
            errors.extend(self._validate_group_groups_schema(df))
        elif schema == "User_Roles":
            errors.extend(self._validate_user_roles_schema(df))
        elif schema == "Group_Roles":
            errors.extend(self._validate_group_roles_schema(df))
        else:
            errors.append(f"Unknown schema: {schema}")

        return errors

    def _validate_users_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate Users schema."""
        errors = []

        # Check for required fields
        required_fields = ["enabled", "created_at", "updated_at", "last_login_at"]
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"Missing required field: {field}")

        # Check for at least one identifier field
        identifier_fields = ["user_id", "username", "email"]
        has_identifier = any(field in df.columns for field in identifier_fields)
        if not has_identifier:
            errors.append("At least one of user_id, username, or email must be present")

        # Check for name fields
        if "full_name" not in df.columns and not (
            "first_name" in df.columns and "last_name" in df.columns
        ):
            errors.append(
                "Either full_name or both first_name and last_name must be present"
            )

        # Validate datetime fields
        datetime_fields = ["created_at", "updated_at", "last_login_at"]
        for field in datetime_fields:
            if field in df.columns:
                try:
                    # Try to parse the datetime string
                    dates = pd.to_datetime(df[field])
                    # Check if any date is missing timezone information
                    if any(date.tzinfo is None for date in dates):
                        errors.append(
                            f"Invalid datetime format in {field} - must be ISO 8601 with timezone"
                        )
                except (ValueError, TypeError):
                    errors.append(f"Invalid datetime format in {field}")

        return errors

    def _validate_groups_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate Groups schema."""
        errors = []

        # Check for at least one identifier
        if not any(col in df.columns for col in ["group_id", "group_name"]):
            errors.append("At least one of group_id or group_name must be present")

        # Check description when group_name is present
        if "group_name" in df.columns and "description" not in df.columns:
            errors.append("Description is required when group_name is present")

        return errors

    def _validate_roles_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate Roles schema."""
        errors = []

        # Check for at least one identifier
        if not any(col in df.columns for col in ["role_id", "role_name"]):
            errors.append("At least one of role_id or role_name must be present")

        # Check description
        if "description" not in df.columns:
            errors.append("Description is required for roles")

        return errors

    def _validate_user_groups_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate User_Groups schema."""
        errors = []

        required_cols = ["user_id", "group_id"]
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
            elif df[col].isnull().any():
                errors.append(f"Column {col} contains null values")

        return errors

    def _validate_group_groups_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate Group_Groups schema."""
        errors = []

        required_cols = ["parent_group_id", "child_group_id"]
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
            elif df[col].isnull().any():
                errors.append(f"Column {col} contains null values")

        return errors

    def _validate_user_roles_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate User_Roles schema."""
        errors = []

        required_cols = ["user_id", "role_id"]
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
            elif df[col].isnull().any():
                errors.append(f"Column {col} contains null values")

        return errors

    def _validate_group_roles_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate Group_Roles schema."""
        errors = []

        required_cols = ["group_id", "role_id"]
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
            elif df[col].isnull().any():
                errors.append(f"Column {col} contains null values")

        return errors

    def validate_relationships(
        self,
        users_df: pd.DataFrame,
        groups_df: pd.DataFrame,
        user_groups_df: pd.DataFrame,
        group_groups_df: pd.DataFrame,
    ) -> List[str]:
        """Validate relationships between entities."""
        errors = []

        # Validate user references
        if "user_id" in user_groups_df.columns:
            invalid_users = set(user_groups_df["user_id"]) - set(users_df["user_id"])
            if invalid_users:
                errors.append(f"Invalid user_ids in User_Groups: {invalid_users}")

        # Validate group references
        if "group_id" in user_groups_df.columns:
            invalid_groups = set(user_groups_df["group_id"]) - set(
                groups_df["group_id"]
            )
            if invalid_groups:
                errors.append(f"Invalid group_ids in User_Groups: {invalid_groups}")

        # Validate parent-child group relationships
        if not group_groups_df.empty:
            parent_groups = set(group_groups_df["parent_group_id"])
            child_groups = set(group_groups_df["child_group_id"])
            all_groups = set(groups_df["group_id"])

            invalid_parents = parent_groups - all_groups
            if invalid_parents:
                errors.append(f"Invalid parent_group_ids: {invalid_parents}")

            invalid_children = child_groups - all_groups
            if invalid_children:
                errors.append(f"Invalid child_group_ids: {invalid_children}")

            # Check for circular references
            if self._has_circular_references(group_groups_df):
                errors.append("Circular reference detected in group relationships")

        return errors

    def _has_circular_references(self, group_groups_df: pd.DataFrame) -> bool:
        """Check for circular references in group relationships."""
        if group_groups_df.empty:
            return False

        # Build adjacency list
        graph: Dict[str, Set[str]] = {}
        for _, row in group_groups_df.iterrows():
            parent = row["parent_group_id"]
            child = row["child_group_id"]
            if parent not in graph:
                graph[parent] = set()
            graph[parent].add(child)

        # Helper function for DFS
        def has_cycle(node: str, visited: Set[str], path: Set[str]) -> bool:
            visited.add(node)
            path.add(node)

            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        if has_cycle(neighbor, visited, path):
                            return True
                    elif neighbor in path:
                        return True

            path.remove(node)
            return False

        # Check each node for cycles
        visited: Set[str] = set()
        path: Set[str] = set()
        for node in graph:
            if node not in visited:
                if has_cycle(node, visited, path):
                    return True

        return False
