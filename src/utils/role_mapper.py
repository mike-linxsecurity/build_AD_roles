"""Map Active Directory groups to roles based on predefined rules.

This module handles the mapping of AD groups to roles, including the creation
of role-group relationships and role hierarchies.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Union

import pandas as pd

logger = logging.getLogger(__name__)


class RoleMapper:
    """Map AD groups to roles based on predefined rules."""

    def __init__(self, builtin_groups_file: Union[str, Path]):
        """Initialize RoleMapper with builtin groups configuration.

        Args:
            builtin_groups_file: Path to JSON file containing builtin group definitions
        """
        self.builtin_groups = self._load_builtin_groups(builtin_groups_file)

    def _load_builtin_groups(self, builtin_groups_file: Union[str, Path]) -> Set[str]:
        """Load builtin groups configuration from JSON file.

        Args:
            builtin_groups_file: Path to JSON file containing builtin group definitions

        Returns:
            Set of role-eligible group names

        Raises:
            FileNotFoundError: If builtin_groups_file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        try:
            with open(builtin_groups_file) as f:
                config = json.load(f)

            # Collect all role-eligible groups from all categories
            role_groups = set()
            for category in ["Original_Role_Groups", "Additional_Role_Groups"]:
                if category in config:
                    role_groups.update(config[category])
            return role_groups

        except FileNotFoundError:
            logger.error("❌ Builtin groups file not found")
            raise
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON in builtin groups file")
            raise

    def create_role_mappings(self, groups_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create role mappings from AD groups.

        Args:
            groups_df: DataFrame containing AD group information

        Returns:
            Dict containing 'Roles' and 'Role_Groups' DataFrames
        """
        roles = []
        role_groups = []

        for _, group in groups_df.iterrows():
            if group["group_name"] in self.builtin_groups:
                # Create role entry
                role = {
                    "role_id": group["group_id"],
                    "role_name": group["group_name"],
                    "description": group.get("description", ""),
                }
                roles.append(role)

                # Create role-group mapping
                role_group = {
                    "group_id": group["group_id"],
                    "role_id": group["group_id"],
                }
                role_groups.append(role_group)

        # Create DataFrames
        roles_df = (
            pd.DataFrame(roles)
            if roles
            else pd.DataFrame(columns=["role_id", "role_name", "description"])
        )
        role_groups_df = (
            pd.DataFrame(role_groups)
            if role_groups
            else pd.DataFrame(columns=["group_id", "role_id"])
        )

        return {"Roles": roles_df, "Role_Groups": role_groups_df}

    def create_role_group_mappings(
        self, sheets: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Create role-group mappings including group hierarchy relationships.

        Args:
            sheets: Dict containing 'Groups' and optionally 'Group_Groups' DataFrames

        Returns:
            DataFrame containing role-group mappings
        """
        # Get initial role mappings
        role_mappings = self.create_role_mappings(sheets["Groups"])
        role_groups_df = role_mappings["Role_Groups"]

        # If there are no group hierarchies, return the direct mappings
        if "Group_Groups" not in sheets or sheets["Group_Groups"].empty:
            return role_groups_df

        # Process group hierarchies
        group_groups_df = sheets["Group_Groups"]
        new_mappings = []

        for _, row in group_groups_df.iterrows():
            parent_id = row["source_group_id"]
            child_id = row["destination_group_id"]

            # If parent has roles, child inherits them
            parent_roles = role_groups_df[role_groups_df["group_id"] == parent_id]
            for _, parent_role in parent_roles.iterrows():
                new_mappings.append(
                    {"group_id": child_id, "role_id": parent_role["role_id"]}
                )

        # Add new mappings if any were created
        if new_mappings:
            new_mappings_df = pd.DataFrame(new_mappings)
            role_groups_df = pd.concat(
                [role_groups_df, new_mappings_df], ignore_index=True
            )
            role_groups_df = role_groups_df.drop_duplicates()

        return role_groups_df

    def resolve_user_roles(
        self, user_groups_df: pd.DataFrame, role_groups_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Resolve user role assignments based on group memberships.

        Args:
            user_groups_df: DataFrame containing user-group relationships
            role_groups_df: DataFrame containing role-group mappings

        Returns:
            DataFrame containing user-role assignments
        """
        # Merge user-group relationships with role-group mappings
        user_roles = pd.merge(
            user_groups_df, role_groups_df, on="group_id", how="inner"
        )

        # Select and rename columns
        user_roles = user_roles[["user_id", "role_id"]].drop_duplicates()

        return user_roles
