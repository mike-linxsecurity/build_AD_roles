"""Role mapping utilities for AD Role Mapping Tool."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class RoleMapper:
    """Class for mapping roles based on group memberships."""

    def __init__(self, builtin_groups_file: str):
        """Initialize RoleMapper with path to builtin groups file."""
        self.builtin_groups_file = builtin_groups_file
        self.role_groups = self._load_role_groups()
        logger.debug(f"Loaded role groups: {self.role_groups}")

    def _load_role_groups(self) -> Dict[str, Set[str]]:
        """Load role groups from configuration file."""
        if not Path(self.builtin_groups_file).exists():
            raise FileNotFoundError(
                f"Builtin groups file not found: {self.builtin_groups_file}"
            )

        with open(self.builtin_groups_file) as f:
            config = json.load(f)

        role_groups = {}

        # Handle format with "groups" key containing list of group objects
        if "groups" in config:
            # Convert to category format
            role_groups["Original_Role_Groups"] = set()
            for group in config["groups"]:
                role_groups["Original_Role_Groups"].add(group["name"])
        else:
            # Handle format with categories mapping to lists of group names
            role_groups = {category: set(groups) for category, groups in config.items()}

        logger.debug(f"Loaded role groups: {role_groups}")
        return role_groups

    def create_role_mappings(
        self, input_groups: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """Create role and group-role mappings based on input groups."""
        roles = []
        group_roles = []

        # Create a set of input group names (case-insensitive)
        input_group_names = {
            name.lower(): (idx, name)
            for idx, name in zip(input_groups["group_id"], input_groups["group_name"])
        }

        # Process each category of role groups
        for category, role_groups in self.role_groups.items():
            # Check each role group
            for role_group in role_groups:
                role_group_lower = role_group.lower()
                if role_group_lower in input_group_names:
                    group_id, group_name = input_group_names[role_group_lower]
                    role_id = f"R_{group_name}"  # Use the original group name
                    roles.append(
                        {
                            "role_id": role_id,
                            "role_name": group_name,  # Use the original group name
                            "description": f"Role for {group_name}",
                            "source": category,
                        }
                    )
                    group_roles.append({"group_id": group_id, "role_id": role_id})

        logger.info(
            f"Created {len(roles)} roles and {len(group_roles)} group-role mappings"
        )

        # Create DataFrames with required columns
        roles_df = (
            pd.DataFrame(roles)
            if roles
            else pd.DataFrame(columns=["role_id", "role_name", "description", "source"])
        )
        group_roles_df = (
            pd.DataFrame(group_roles)
            if group_roles
            else pd.DataFrame(columns=["group_id", "role_id"])
        )

        # Ensure required columns are present
        if not roles_df.empty:
            roles_df = roles_df[["role_id", "role_name", "description", "source"]]
        if not group_roles_df.empty:
            group_roles_df = group_roles_df[["group_id", "role_id"]]

        return {"Roles": roles_df, "Group_Roles": group_roles_df}

    def resolve_group_roles(
        self,
        roles_df: pd.DataFrame,
        group_groups_df: pd.DataFrame,
        groups_df: pd.DataFrame = None,
        group_roles_df: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """Resolve group-role relationships based on group-group relationships.

        Args:
            roles_df: DataFrame containing role definitions
            group_groups_df: DataFrame containing group hierarchy relationships
            groups_df: DataFrame containing group information (optional)
            group_roles_df: DataFrame containing direct group-role mappings (optional)

        Returns:
            DataFrame containing group-role assignments including inherited roles
        """
        if group_groups_df.empty or group_roles_df is None or group_roles_df.empty:
            return (
                group_roles_df
                if group_roles_df is not None
                else pd.DataFrame(columns=["group_id", "role_id"])
            )

        # Create a mapping of child groups to their parent groups
        child_to_parent = {}
        for _, row in group_groups_df.iterrows():
            child = row["child_group_id"]
            parent = row["parent_group_id"]
            if child not in child_to_parent:
                child_to_parent[child] = set()
            child_to_parent[child].add(parent)

        # Helper function to get all parent groups recursively
        def get_all_parents(group_id: str, visited: Set[str] = None) -> Set[str]:
            if visited is None:
                visited = set()
            if group_id in visited:
                return set()
            visited.add(group_id)
            parents = child_to_parent.get(group_id, set())
            all_parents = parents.copy()
            for parent in parents:
                all_parents.update(get_all_parents(parent, visited))
            return all_parents

        # Process all groups and their roles
        resolved_roles = []
        processed_combinations = set()

        # Get all unique groups
        all_groups = set(group_roles_df["group_id"].unique())
        if not group_groups_df.empty:
            all_groups.update(group_groups_df["parent_group_id"].unique())
            all_groups.update(group_groups_df["child_group_id"].unique())

        for group_id in all_groups:
            # Get all parent groups
            parent_groups = get_all_parents(group_id)
            parent_groups.add(group_id)  # Include the group itself

            # Add roles from all parent groups
            for parent_id in parent_groups:
                parent_roles = group_roles_df[group_roles_df["group_id"] == parent_id]
                for _, role_row in parent_roles.iterrows():
                    combination = (group_id, role_row["role_id"])
                    if combination not in processed_combinations:
                        resolved_roles.append(
                            {"group_id": group_id, "role_id": role_row["role_id"]}
                        )
                        processed_combinations.add(combination)

        # Create final DataFrame
        result_df = pd.DataFrame(resolved_roles)
        if result_df.empty:
            result_df = pd.DataFrame(columns=["group_id", "role_id"])

        return result_df.drop_duplicates()

    def resolve_user_roles(
        self, user_groups_df: pd.DataFrame, group_roles_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Create user-role relationships based on user-group and group-role relationships.

        Args:
            user_groups_df: DataFrame containing user-group memberships
            group_roles_df: DataFrame containing group-role assignments

        Returns:
            DataFrame containing user-role assignments
        """
        if user_groups_df.empty or group_roles_df.empty:
            return pd.DataFrame(columns=["user_id", "role_id"])

        # Merge user-group and group-role relationships
        user_roles = user_groups_df.merge(group_roles_df, on="group_id")[
            ["user_id", "role_id"]
        ]
        return user_roles.drop_duplicates()
