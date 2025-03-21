"""Tests for Excel file handling utilities."""

import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.utils.excel_handler import ExcelHandler


@pytest.fixture
def excel_handler():
    """Create ExcelHandler instance for testing."""
    return ExcelHandler()


def test_required_field_combinations(excel_handler):
    """Test validation of required field combinations."""
    # Test Users sheet with only user_id and full_name
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "full_name": ["John Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    assert excel_handler._validate_users_sheet(users_df) == []

    # Test Users sheet with username and first_name/last_name
    users_df = pd.DataFrame(
        {
            "username": ["user1"],
            "first_name": ["John"],
            "last_name": ["Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    assert excel_handler._validate_users_sheet(users_df) == []

    # Test Users sheet with email and full_name
    users_df = pd.DataFrame(
        {
            "email": ["user1@test.com"],
            "full_name": ["John Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    assert excel_handler._validate_users_sheet(users_df) == []

    # Test Users sheet with missing all identifiers
    users_df = pd.DataFrame(
        {
            "full_name": ["John Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    errors = excel_handler._validate_users_sheet(users_df)
    assert len(errors) > 0
    assert any(
        "At least one of user_id, username, or email must be present" in error
        for error in errors
    )

    # Test Users sheet with missing name fields
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    errors = excel_handler._validate_users_sheet(users_df)
    assert len(errors) > 0
    assert any(
        "Either full_name or both first_name and last_name must be present" in error
        for error in errors
    )


def test_datetime_format_validation(excel_handler):
    """Test validation of datetime formats."""
    # Test valid ISO 8601 format
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "full_name": ["John Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    assert excel_handler._validate_users_sheet(users_df) == []

    # Test invalid datetime format
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "full_name": ["John Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20"],  # Invalid format
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    errors = excel_handler._validate_users_sheet(users_df)
    assert len(errors) == 1
    assert "Invalid datetime format in created_at" in errors[0]


def test_name_field_validation(excel_handler):
    """Test validation of name field requirements."""
    # Test with full_name only
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "full_name": ["John Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    assert excel_handler._validate_users_sheet(users_df) == []

    # Test with first_name and last_name
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "first_name": ["John"],
            "last_name": ["Doe"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    assert excel_handler._validate_users_sheet(users_df) == []

    # Test with missing name fields
    users_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "enabled": ["Yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    errors = excel_handler._validate_users_sheet(users_df)
    assert len(errors) == 1
    assert (
        "Either full_name or both first_name and last_name must be present" in errors[0]
    )


def test_group_validation(excel_handler):
    """Test validation of group data."""
    # Test valid group data with group_name and description
    groups_df = pd.DataFrame({"group_name": ["Admins"], "description": ["Admin group"]})
    assert excel_handler._validate_groups_sheet(groups_df) == []

    # Test missing description when group_name is present
    groups_df = pd.DataFrame({"group_name": ["Admins"]})
    errors = excel_handler._validate_groups_sheet(groups_df)
    assert len(errors) > 0
    assert any(
        "Description is required when group_name is present" in error
        for error in errors
    )


def test_role_validation(excel_handler):
    """Test validation of role data."""
    # Test valid role data
    roles_df = pd.DataFrame(
        {"role_id": ["R1"], "role_name": ["Admin"], "description": ["Admin role"]}
    )
    assert excel_handler._validate_roles_sheet(roles_df) == []

    # Test missing description
    roles_df = pd.DataFrame({"role_id": ["R1"], "role_name": ["Admin"]})
    errors = excel_handler._validate_roles_sheet(roles_df)
    assert len(errors) > 0
    assert any("Description is required" in error for error in errors)


def test_relationship_validation(excel_handler):
    """Test validation of relationship data."""
    # Test valid User_Groups data
    user_groups_df = pd.DataFrame({"user_id": ["U1"], "group_id": ["G1"]})
    assert excel_handler._validate_user_groups_sheet(user_groups_df) == []

    # Test valid Group_Groups data
    group_groups_df = pd.DataFrame(
        {"parent_group_id": ["G1"], "child_group_id": ["G2"]}
    )
    assert excel_handler._validate_group_groups_sheet(group_groups_df) == []

    # Test missing required fields in User_Groups
    user_groups_df = pd.DataFrame({"user_id": ["U1"]})
    errors = excel_handler._validate_user_groups_sheet(user_groups_df)
    assert len(errors) > 0
    assert any("Missing required column: group_id" in error for error in errors)

    # Test missing required fields in Group_Groups
    group_groups_df = pd.DataFrame({"parent_group_id": ["G1"]})
    errors = excel_handler._validate_group_groups_sheet(group_groups_df)
    assert len(errors) > 0
    assert any("Missing required column: child_group_id" in error for error in errors)
