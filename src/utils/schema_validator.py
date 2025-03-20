"""Schema validation utilities for AD Role Mapping Tool."""

import logging
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
    """Validates data against predefined schemas."""

    @staticmethod
    def validate_dataframe(df: DataFrame, schema_name: str) -> List[str]:
        """Validate a DataFrame against its schema.

        Args:
            df: DataFrame to validate
            schema_name: Name of the schema to validate against

        Returns:
            List[str]: List of validation errors
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
                errors.append(f"Missing required field: {field}")
            else:
                # Type validation (basic)
                try:
                    if field_type == bool:
                        # Handle boolean fields that might be "yes"/"no" strings
                        if not all(str(x).lower() in ['true', 'false', 'yes', 'no', '1', '0'] 
                                 for x in df[field].dropna()):
                            errors.append(f"Invalid boolean values in field: {field}")
                    else:
                        df[field].astype(field_type)
                except (ValueError, TypeError):
                    errors.append(f"Invalid type for field {field}, expected {field_type.__name__}")

        # Validate conditional requirements
        for condition in schema.get("conditional_required", []):
            fields = condition["fields"]
            min_required = condition["min_required"]
            present_fields = [f for f in fields if f in df.columns and not df[f].isna().all()]
            
            if len(present_fields) < min_required:
                errors.append(condition["message"])

        return errors

    @staticmethod
    def validate_relationships(users_df: DataFrame, groups_df: DataFrame, 
                             user_groups_df: DataFrame, group_groups_df: DataFrame) -> List[str]:
        """Validate relationships between different entities.

        Args:
            users_df: Users DataFrame
            groups_df: Groups DataFrame
            user_groups_df: User-Group relationships DataFrame
            group_groups_df: Group-Group relationships DataFrame

        Returns:
            List[str]: List of validation errors
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