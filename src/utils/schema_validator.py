"""Schema validation utilities for AD Role Mapping Tool.

This module provides validation functionality for Active Directory data schemas and relationships.
It ensures that input data meets the required format and constraints before processing.

The module defines validation rules for:
- Users: AD user attributes and required fields
- Groups: AD group attributes and hierarchical relationships
- Roles: Role definitions mapped from AD groups
- Relationships: User-Group and Group-Group relationships

Example:
    validator = SchemaValidator()
    users_df = pd.DataFrame({...})
    errors = validator.validate_dataframe(users_df, "Users")
    if errors:
        print("Validation failed:", errors)
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)

SCHEMA_RULES = {
    "Users": {
        "required_fields": {
            "user_id": str,
            "username": str,
            "email": str,
            "full_name": str,
            "enabled": bool,
            "created_at": str,
            "updated_at": str,
            "last_login_at": str
        },
        "datetime_fields": ["created_at", "updated_at", "last_login_at"],
        "conditional_required": [
            {
                "fields": ["user_id", "username", "email"],
                "min_required": 1,
                "message": "At least one of user_id, username, or email must be present"
            },
            {
                "fields": ["full_name", "first_name", "last_name"],
                "min_required": 2,
                "message": "Either full_name or (first_name + last_name) must be present"
            }
        ]
    },
    "Groups": {
        "required_fields": {
            "group_id": str,
            "group_name": str,
            "description": str
        },
        "conditional_required": [
            {
                "fields": ["group_id", "group_name"],
                "min_required": 1,
                "message": "At least one of group_id or group_name must be present"
            }
        ]
    },
    "Roles": {
        "required_fields": {
            "role_id": str,
            "role_name": str,
            "description": str
        },
        "conditional_required": [
            {
                "fields": ["role_id", "role_name"],
                "min_required": 1,
                "message": "At least one of role_id or role_name must be present"
            }
        ]
    }
}


class SchemaValidator:
    """Validates data against predefined schemas for AD Role Mapping.
    
    This class provides methods to validate:
    1. DataFrame schemas for Users, Groups, and Roles
    2. Relationships between entities (User-Group and Group-Group)
    3. Data types and formats (e.g., datetime fields, boolean values)
    4. Conditional field requirements
    
    The validator uses the SCHEMA_RULES dictionary to define validation rules
    for each entity type. It supports:
    - Required field validation
    - Data type checking
    - Conditional field requirements
    - ISO 8601 datetime format validation
    - Boolean field validation (true/false/yes/no/1/0)
    """

    @staticmethod
    def _is_valid_datetime(value: str) -> bool:
        """Check if a string is a valid ISO 8601 datetime.

        The method validates that the datetime string follows the ISO 8601 format
        and represents a valid date and time.

        Args:
            value: String to validate, expected in ISO 8601 format
                  (e.g., "2024-03-20T12:00:00Z" or "2024-03-20T12:00:00+00:00")

        Returns:
            bool: True if the string is a valid ISO 8601 datetime, False otherwise

        Note:
            - Handles both 'Z' and explicit timezone offset formats
            - Converts 'Z' to '+00:00' for parsing
            - Returns False for None values or non-string inputs
        """
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def validate_dataframe(df: DataFrame, schema_name: str) -> List[str]:
        """Validate a DataFrame against its schema.

        Performs comprehensive validation of a DataFrame against the predefined
        schema rules, including field presence, data types, and conditional
        requirements.

        Args:
            df: DataFrame to validate, containing the data to check
            schema_name: Name of the schema to validate against ("Users", "Groups", or "Roles")

        Returns:
            List[str]: List of validation error messages. Empty list if validation passes.

        Examples:
            >>> users_df = pd.DataFrame({
            ...     "user_id": ["U1"],
            ...     "email": ["user@example.com"],
            ...     "full_name": ["John Doe"],
            ...     "enabled": ["yes"],
            ...     "created_at": ["2024-03-20T12:00:00Z"]
            ... })
            >>> errors = SchemaValidator.validate_dataframe(users_df, "Users")
            >>> print(errors)
            ['Missing required field: username', 'Missing required field: updated_at']

        Note:
            - Returns early with error if schema_name is unknown or DataFrame is empty
            - Validates both required and conditional field requirements
            - Performs type validation for all fields
            - Special handling for boolean and datetime fields
        """
        errors = []
        schema = SCHEMA_RULES.get(schema_name)
        
        if not schema:
            return [f"No schema defined for {schema_name}"]
        
        if df.empty:
            return [f"DataFrame for {schema_name} is empty"]

        # Validate required fields
        for field, field_type in schema["required_fields"].items():
            if field not in df.columns:
                # Check conditional requirements before reporting missing field
                is_conditionally_required = any(
                    field in condition["fields"] 
                    for condition in schema.get("conditional_required", [])
                )
                if not is_conditionally_required:
                    errors.append(f"Missing required field: {field}")
            else:
                # Type validation
                try:
                    if field_type == bool:
                        # Handle boolean fields that might be "yes"/"no" strings
                        if not all(str(x).lower() in ['true', 'false', 'yes', 'no', '1', '0'] 
                                 for x in df[field].dropna()):
                            errors.append(f"Invalid boolean values in field: {field}")
                    elif field in schema.get("datetime_fields", []):
                        # Validate datetime fields
                        invalid_dates = [
                            str(x) for x in df[field].dropna() 
                            if not SchemaValidator._is_valid_datetime(str(x))
                        ]
                        if invalid_dates:
                            errors.append(
                                f"Invalid datetime values in field {field}: {invalid_dates}"
                            )
                    else:
                        df[field].astype(field_type)
                except (ValueError, TypeError):
                    errors.append(f"Invalid type for field {field}, expected {field_type.__name__}")

        # Validate conditional requirements
        for condition in schema.get("conditional_required", []):
            fields = condition["fields"]
            min_required = condition["min_required"]
            
            # Check if the required fields exist in the DataFrame
            present_fields = [f for f in fields if f in df.columns]
            if len(present_fields) < min_required:
                errors.append(condition["message"])
                continue
            
            # For each row, check if the condition is met
            for idx, row in df.iterrows():
                valid_fields = [f for f in present_fields if pd.notna(row.get(f))]
                if len(valid_fields) < min_required:
                    errors.append(f"Row {idx}: {condition['message']}")

        return errors

    @staticmethod
    def validate_relationships(users_df: DataFrame, groups_df: DataFrame, 
                             user_groups_df: DataFrame, group_groups_df: DataFrame) -> List[str]:
        """Validate relationships between different entities.

        Performs comprehensive validation of relationships between users, groups,
        and nested group hierarchies. Checks for:
        1. Valid user references in User-Group relationships
        2. Valid group references in both User-Group and Group-Group relationships
        3. Circular dependencies in group hierarchies

        Args:
            users_df: Users DataFrame containing user records
            groups_df: Groups DataFrame containing group records
            user_groups_df: User-Group relationships DataFrame
            group_groups_df: Group-Group relationships DataFrame (nested groups)

        Returns:
            List[str]: List of validation error messages. Empty list if validation passes.

        Examples:
            >>> users_df = pd.DataFrame({"user_id": ["U1"]})
            >>> groups_df = pd.DataFrame({"group_id": ["G1", "G2"]})
            >>> user_groups = pd.DataFrame({"user_id": ["U1"], "group_id": ["G1"]})
            >>> group_groups = pd.DataFrame({
            ...     "parent_group_id": ["G1"],
            ...     "child_group_id": ["G2"]
            ... })
            >>> errors = SchemaValidator.validate_relationships(
            ...     users_df, groups_df, user_groups, group_groups
            ... )
            >>> print(errors)
            []

        Note:
            - Handles empty DataFrames gracefully
            - Detects both direct and indirect circular references
            - Uses set operations for efficient ID validation
            - Implements depth-first search for cycle detection
        """
        errors = []
        
        # Validate User-Group relationships
        if not user_groups_df.empty:
            invalid_users = set(user_groups_df['user_id']) - set(users_df['user_id'])
            if invalid_users:
                errors.append(f"Invalid user_ids in User_Groups: {invalid_users}")
            
            invalid_groups = set(user_groups_df['group_id']) - set(groups_df['group_id'])
            if invalid_groups:
                errors.append(f"Invalid group_ids in User_Groups: {invalid_groups}")

        # Validate Group-Group relationships
        if not group_groups_df.empty:
            all_group_ids = set(groups_df['group_id'])
            invalid_parents = set(group_groups_df['parent_group_id']) - all_group_ids
            if invalid_parents:
                errors.append(f"Invalid parent_group_ids in Group_Groups: {invalid_parents}")
            
            invalid_children = set(group_groups_df['child_group_id']) - all_group_ids
            if invalid_children:
                errors.append(f"Invalid child_group_ids in Group_Groups: {invalid_children}")

            # Check for circular references
            from collections import defaultdict
            graph = defaultdict(list)
            for _, row in group_groups_df.iterrows():
                graph[row['parent_group_id']].append(row['child_group_id'])
            
            visited = set()
            path = set()
            
            def has_cycle(node: str) -> bool:
                """Check for cycles in the group hierarchy using DFS.
                
                Args:
                    node: Current group ID being checked
                
                Returns:
                    bool: True if a cycle is detected, False otherwise
                """
                if node in path:
                    return True
                if node in visited:
                    return False
                    
                visited.add(node)
                path.add(node)
                
                for child in graph[node]:
                    if has_cycle(child):
                        return True
                        
                path.remove(node)
                return False

            for group_id in graph:
                if has_cycle(group_id):
                    errors.append(f"Circular reference detected in group relationships starting from: {group_id}")
                    break

        return errors