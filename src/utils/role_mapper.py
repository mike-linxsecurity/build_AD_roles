"""Role mapping utilities for AD Role Mapping Tool."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)


class RoleMapper:
    """Maps AD groups to roles and resolves role assignments."""

    def __init__(self, builtin_groups_file: Path):
        """Initialize RoleMapper with builtin groups configuration.

        Args:
            builtin_groups_file: Path to the builtin_groups.json file.
        """
        self.builtin_groups_file = Path(builtin_groups_file)
        if not self.builtin_groups_file.exists():
            raise FileNotFoundError(f"Builtin groups file not found: {self.builtin_groups_file}")
        
        with open(self.builtin_groups_file) as f:
            self.group_config = json.load(f)
        
        # Create a flattened set of all role-eligible groups, with Original_Role_Groups taking precedence
        self.role_groups = set(self.group_config.get("Original_Role_Groups", []))
        for category, groups in self.group_config.items():
            if category != "Original_Role_Groups":
                self.role_groups.update(groups)

    def create_role_mappings(self, groups_df: DataFrame) -> DataFrame:
        """Create role mappings from AD groups.

        Args:
            groups_df: DataFrame containing group information.

        Returns:
            DataFrame: Role mappings with role_id, role_name, and description.
        """
        role_data = []
        
        # First map Original_Role_Groups
        original_roles = set(self.group_config.get("Original_Role_Groups", []))
        for _, group in groups_df.iterrows():
            if group["group_name"] in original_roles:
                role_data.append({
                    "role_id": group["group_id"],
                    "role_name": group["group_name"],
                    "description": group.get("description", f"Role based on {group['group_name']} group"),
                    "source": "Original_Role_Groups"
                })
        
        # Then map other eligible groups that aren't already mapped
        mapped_groups = {role["role_name"] for role in role_data}
        for _, group in groups_df.iterrows():
            if group["group_name"] in self.role_groups and group["group_name"] not in mapped_groups:
                # Find which category this group belongs to
                category = next((cat for cat, groups in self.group_config.items() 
                               if group["group_name"] in groups), "Unknown")
                role_data.append({
                    "role_id": group["group_id"],
                    "role_name": group["group_name"],
                    "description": group.get("description", f"Role based on {group['group_name']} group"),
                    "source": category
                })
        
        return pd.DataFrame(role_data)

    def resolve_group_roles(self, roles_df: DataFrame, group_groups_df: DataFrame) -> DataFrame:
        """Resolve group-role relationships including inherited roles.

        Args:
            roles_df: DataFrame containing role definitions
            group_groups_df: DataFrame containing group-group relationships

        Returns:
            DataFrame: Group-role mappings including inherited roles
        """
        group_roles = []
        processed_groups = set()
        
        def get_inherited_roles(group_id: str, visited: Set[str]) -> Set[str]:
            """Recursively get all inherited role IDs for a group."""
            if group_id in visited:
                return set()
            
            visited.add(group_id)
            inherited = {group_id} if group_id in roles_df["role_id"].values else set()
            
            # Get all parent groups
            parent_groups = group_groups_df[group_groups_df["child_group_id"] == group_id]["parent_group_id"]
            for parent_id in parent_groups:
                inherited.update(get_inherited_roles(parent_id, visited.copy()))
            
            return inherited

        # Process each group in the group-group relationships
        all_groups = pd.concat([
            group_groups_df["parent_group_id"],
            group_groups_df["child_group_id"]
        ]).unique()

        for group_id in all_groups:
            if group_id in processed_groups:
                continue
                
            # Get all roles this group inherits
            role_ids = get_inherited_roles(group_id, set())
            
            # Add group-role mappings
            for role_id in role_ids:
                if role_id in roles_df["role_id"].values:
                    group_roles.append({
                        "group_id": group_id,
                        "role_id": role_id
                    })
            
            processed_groups.add(group_id)

        return pd.DataFrame(group_roles)

    def resolve_user_roles(self, user_groups_df: DataFrame, group_roles_df: DataFrame) -> DataFrame:
        """Resolve user-role relationships based on group memberships.

        Args:
            user_groups_df: DataFrame containing user-group relationships
            group_roles_df: DataFrame containing group-role relationships

        Returns:
            DataFrame: User-role mappings
        """
        # Merge user-group relationships with group-role mappings
        user_roles = pd.merge(
            user_groups_df,
            group_roles_df,
            left_on="group_id",
            right_on="group_id",
            how="inner"
        )[["user_id", "role_id"]].drop_duplicates()

        return user_roles 