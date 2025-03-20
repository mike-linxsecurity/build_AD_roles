"""Tests for role_mapper module."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.utils.role_mapper import RoleMapper


@pytest.fixture
def sample_groups_df():
    """Create sample groups DataFrame."""
    return pd.DataFrame({
        "group_id": ["G1", "G2", "G3", "G4"],
        "group_name": ["Administrators", "Users", "Exchange Admins", "Custom Group"],
        "description": ["Admin Group", "Regular Users", "Exchange Admins", "Custom Group"]
    })


@pytest.fixture
def sample_group_groups_df():
    """Create sample group-group relationships DataFrame."""
    return pd.DataFrame({
        "parent_group_id": ["G1", "G2"],
        "child_group_id": ["G2", "G3"]
    })


@pytest.fixture
def sample_user_groups_df():
    """Create sample user-group relationships DataFrame."""
    return pd.DataFrame({
        "user_id": ["U1", "U2", "U2"],
        "group_id": ["G1", "G2", "G3"]
    })


def test_role_mapper_init(sample_builtin_groups):
    """Test RoleMapper initialization."""
    mapper = RoleMapper(sample_builtin_groups)
    assert mapper.role_groups == {"Domain Admins", "Administrators", "Users", "Exchange Admins"}

    with pytest.raises(FileNotFoundError):
        RoleMapper(Path("nonexistent.json"))


def test_create_role_mappings(sample_builtin_groups, sample_groups_df):
    """Test creation of role mappings from groups."""
    mapper = RoleMapper(sample_builtin_groups)
    roles_df = mapper.create_role_mappings(sample_groups_df)

    # Check that Original_Role_Groups are mapped first
    assert not roles_df.empty
    original_roles = roles_df[roles_df["source"] == "Original_Role_Groups"]
    assert len(original_roles) == 2  # Administrators and Users
    assert "Administrators" in original_roles["role_name"].values
    assert "Users" in original_roles["role_name"].values

    # Check that other eligible groups are mapped
    other_roles = roles_df[roles_df["source"] == "Exchange_Server_Groups"]
    assert len(other_roles) == 1  # Exchange Admins
    assert "Exchange Admins" in other_roles["role_name"].values

    # Check that non-eligible groups are not mapped
    assert "Custom Group" not in roles_df["role_name"].values


def test_resolve_group_roles(sample_builtin_groups, sample_groups_df, sample_group_groups_df):
    """Test resolution of group-role relationships."""
    mapper = RoleMapper(sample_builtin_groups)
    roles_df = mapper.create_role_mappings(sample_groups_df)
    group_roles_df = mapper.resolve_group_roles(roles_df, sample_group_groups_df)

    # Check direct role assignments
    assert not group_roles_df.empty
    g1_roles = group_roles_df[group_roles_df["group_id"] == "G1"]
    assert len(g1_roles) == 1  # G1 (Administrators) has its own role

    # Check inherited roles
    g2_roles = group_roles_df[group_roles_df["group_id"] == "G2"]
    assert len(g2_roles) == 2  # G2 has its own role and inherits from G1

    g3_roles = group_roles_df[group_roles_df["group_id"] == "G3"]
    assert len(g3_roles) == 3  # G3 has its own role and inherits from G1 and G2


def test_resolve_user_roles(sample_builtin_groups, sample_groups_df, 
                          sample_group_groups_df, sample_user_groups_df):
    """Test resolution of user-role relationships."""
    mapper = RoleMapper(sample_builtin_groups)
    roles_df = mapper.create_role_mappings(sample_groups_df)
    group_roles_df = mapper.resolve_group_roles(roles_df, sample_group_groups_df)
    user_roles_df = mapper.resolve_user_roles(sample_user_groups_df, group_roles_df)

    # Check that users get roles from their groups and inherited roles
    assert not user_roles_df.empty
    u1_roles = user_roles_df[user_roles_df["user_id"] == "U1"]
    assert len(u1_roles) == 1  # U1 is in Administrators group

    u2_roles = user_roles_df[user_roles_df["user_id"] == "U2"]
    assert len(u2_roles) == 3  # U2 is in Users and Exchange Admins groups, plus inherited roles 