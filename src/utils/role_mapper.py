"""Role mapping utilities for AD Role Mapping Tool.

This module provides functionality for mapping Active Directory groups to roles
and resolving role assignments for users and groups. It handles:
- Mapping AD groups to roles based on configuration
- Resolving inherited roles through group hierarchies
- Determining user roles based on group memberships

The module uses a configuration file (builtin_groups.json) to define which AD groups
should be mapped to roles, with support for different categories of role groups.

Example:
    mapper = RoleMapper("config/builtin_groups.json")
    roles_df = mapper.create_role_mappings(groups_df)
    group_roles = mapper.resolve_group_roles(roles_df, group_groups_df)
    user_roles = mapper.resolve_user_roles(user_groups_df, group_roles)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)


class RoleMapper:
    """Maps AD groups to roles and resolves role assignments.
    
    This class handles the mapping of Active Directory groups to roles and resolves
    role assignments through group hierarchies. It supports:
    1. Role creation from predefined AD groups
    2. Role inheritance through nested group relationships
    3. User role resolution based on group memberships
    
    The mapping process respects role precedence defined in the builtin_groups.json
    configuration file, where Original_Role_Groups take precedence over other
    role-eligible groups.
    
    Attributes:
        builtin_groups_file (Path): Path to the configuration file
        group_config (Dict): Loaded configuration from builtin_groups.json
        role_groups (Set[str]): Set of all role-eligible group names
    """

    def __init__(self, builtin_groups_file: Path):
        """Initialize RoleMapper with builtin groups configuration.

        Loads and validates the builtin groups configuration file, which defines
        which AD groups should be mapped to roles and their categories.

        Args:
            builtin_groups_file: Path to the builtin_groups.json file that defines
                               role-eligible groups and their categories.

        Raises:
            FileNotFoundError: If the builtin_groups.json file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            
        Example:
            >>> mapper = RoleMapper(Path("config/builtin_groups.json"))
            >>> print(mapper.role_groups)
            {'Admins', 'PowerUsers', 'Developers'}
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

        Maps eligible AD groups to roles based on the builtin groups configuration.
        Original_Role_Groups are processed first to ensure they take precedence
        over other role-eligible groups.

        Args:
            groups_df: DataFrame containing group information with columns:
                      - group_id (str): Unique identifier for the group
                      - group_name (str): Name of the group
                      - description (str, optional): Group description

        Returns:
            DataFrame: Role mappings with columns:
                      - role_id (str): Unique identifier for the role
                      - role_name (str): Name of the role
                      - description (str): Role description
                      - source (str): Category from builtin_groups.json

        Example:
            >>> groups_df = pd.DataFrame({
            ...     "group_id": ["G1", "G2"],
            ...     "group_name": ["Admins", "Users"],
            ...     "description": ["Admin group", "Regular users"]
            ... })
            >>> roles_df = mapper.create_role_mappings(groups_df)
            >>> print(roles_df)
               role_id role_name description        source
            0      G1    Admins Admin group Original_Roles
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

        Determines all roles that each group has, including roles inherited through
        the group hierarchy. A group inherits all roles from its parent groups.

        Args:
            roles_df: DataFrame containing role definitions with columns:
                     - role_id (str): Unique identifier for the role
                     - role_name (str): Name of the role
            group_groups_df: DataFrame containing group-group relationships with columns:
                           - parent_group_id (str): ID of the parent group
                           - child_group_id (str): ID of the child group

        Returns:
            DataFrame: Group-role mappings with columns:
                      - group_id (str): ID of the group
                      - role_id (str): ID of the role (direct or inherited)

        Example:
            >>> roles_df = pd.DataFrame({
            ...     "role_id": ["R1", "R2"],
            ...     "role_name": ["Admin", "User"]
            ... })
            >>> group_groups_df = pd.DataFrame({
            ...     "parent_group_id": ["G1"],
            ...     "child_group_id": ["G2"]
            ... })
            >>> group_roles = mapper.resolve_group_roles(roles_df, group_groups_df)
            >>> print(group_roles)
               group_id role_id
            0       G2      R1  # G2 inherits R1 from G1
        
        Note:
            - Handles circular dependencies in group relationships
            - Processes each group only once for efficiency
            - Includes both direct and inherited role assignments
        """
        group_roles = []
        processed_groups = set()
        
        def get_inherited_roles(group_id: str, visited: Set[str]) -> Set[str]:
            """Recursively get all inherited role IDs for a group.
            
            Traverses the group hierarchy upward to find all roles that this group
            inherits from its parent groups. Handles circular dependencies by
            tracking visited groups.
            
            Args:
                group_id: ID of the group to check
                visited: Set of group IDs already visited in this branch
            
            Returns:
                Set[str]: Set of role IDs that this group has or inherits
            """
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

        Determines all roles that each user has based on their group memberships,
        including roles inherited through group hierarchies.

        Args:
            user_groups_df: DataFrame containing user-group relationships with columns:
                          - user_id (str): ID of the user
                          - group_id (str): ID of the group
            group_roles_df: DataFrame containing group-role relationships with columns:
                          - group_id (str): ID of the group
                          - role_id (str): ID of the role

        Returns:
            DataFrame: User-role mappings with columns:
                      - user_id (str): ID of the user
                      - role_id (str): ID of the role

        Example:
            >>> user_groups_df = pd.DataFrame({
            ...     "user_id": ["U1"],
            ...     "group_id": ["G1"]
            ... })
            >>> group_roles_df = pd.DataFrame({
            ...     "group_id": ["G1"],
            ...     "role_id": ["R1"]
            ... })
            >>> user_roles = mapper.resolve_user_roles(user_groups_df, group_roles_df)
            >>> print(user_roles)
               user_id role_id
            0      U1      R1

        Note:
            - Removes duplicate user-role assignments
            - Only includes roles that come from valid group memberships
            - Uses an inner join to ensure only valid relationships are included
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