"""Tests for schema_validator module."""

import pandas as pd
import pytest

from src.utils.schema_validator import SchemaValidator


def test_validate_users_schema():
    """Test validation of Users schema."""
    # Valid data
    valid_df = pd.DataFrame({
        "user_id": ["U1"],
        "username": ["user1"],
        "email": ["user1@test.com"],
        "full_name": ["User One"],
        "enabled": ["yes"],
        "created_at": ["2024-03-20T12:00:00Z"],
        "updated_at": ["2024-03-20T12:00:00Z"],
        "last_login_at": ["2024-03-20T12:00:00Z"]
    })
    errors = SchemaValidator.validate_dataframe(valid_df, "Users")
    assert not errors, f"Unexpected errors: {errors}"

    # Invalid data - missing required fields
    invalid_df = pd.DataFrame({
        "username": ["user1"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_df, "Users")
    assert errors
    assert any("Missing required field" in error for error in errors)

    # Invalid data - wrong type
    invalid_type_df = pd.DataFrame({
        "user_id": ["U1"],
        "username": ["user1"],
        "email": ["user1@test.com"],
        "full_name": ["User One"],
        "enabled": ["invalid"],  # Invalid boolean value
        "created_at": ["2024-03-20T12:00:00Z"],
        "updated_at": ["2024-03-20T12:00:00Z"],
        "last_login_at": ["2024-03-20T12:00:00Z"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_type_df, "Users")
    assert errors
    assert any("Invalid boolean values" in error for error in errors)


def test_validate_groups_schema():
    """Test validation of Groups schema."""
    # Valid data
    valid_df = pd.DataFrame({
        "group_id": ["G1"],
        "group_name": ["Admins"],
        "description": ["Admin group"]
    })
    errors = SchemaValidator.validate_dataframe(valid_df, "Groups")
    assert not errors, f"Unexpected errors: {errors}"

    # Invalid data - missing required fields
    invalid_df = pd.DataFrame({
        "description": ["Admin group"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_df, "Groups")
    assert errors
    assert any("At least one of group_id or group_name must be present" in error for error in errors)


def test_validate_relationships():
    """Test validation of relationships between entities."""
    users_df = pd.DataFrame({
        "user_id": ["U1", "U2"],
        "username": ["user1", "user2"]
    })
    
    groups_df = pd.DataFrame({
        "group_id": ["G1", "G2"],
        "group_name": ["Group1", "Group2"]
    })
    
    # Valid relationships
    valid_user_groups = pd.DataFrame({
        "user_id": ["U1"],
        "group_id": ["G1"]
    })
    
    valid_group_groups = pd.DataFrame({
        "parent_group_id": ["G1"],
        "child_group_id": ["G2"]
    })
    
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, valid_user_groups, valid_group_groups
    )
    assert not errors, f"Unexpected errors: {errors}"
    
    # Invalid relationships - non-existent IDs
    invalid_user_groups = pd.DataFrame({
        "user_id": ["U3"],  # Non-existent user
        "group_id": ["G3"]  # Non-existent group
    })
    
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, invalid_user_groups, valid_group_groups
    )
    assert errors
    assert any("Invalid user_ids" in error for error in errors)
    assert any("Invalid group_ids" in error for error in errors)
    
    # Test circular reference detection
    circular_group_groups = pd.DataFrame({
        "parent_group_id": ["G1", "G2"],
        "child_group_id": ["G2", "G1"]
    })
    
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, valid_user_groups, circular_group_groups
    )
    assert errors
    assert any("Circular reference detected" in error for error in errors) 