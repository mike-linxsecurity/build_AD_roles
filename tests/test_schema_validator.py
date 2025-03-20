"""Tests for schema_validator module."""

import pandas as pd
import pytest
from datetime import datetime

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

    # Test conditional field requirements
    conditional_df = pd.DataFrame({
        "email": ["user1@test.com"],  # Only email present
        "full_name": ["User One"],
        "enabled": ["yes"],
        "created_at": ["2024-03-20T12:00:00Z"],
        "updated_at": ["2024-03-20T12:00:00Z"],
        "last_login_at": ["2024-03-20T12:00:00Z"]
    })
    errors = SchemaValidator.validate_dataframe(conditional_df, "Users")
    assert not errors, "Should accept data with only email present"

    # Test name field combinations
    name_combinations_df = pd.DataFrame({
        "user_id": ["U1"],
        "username": ["user1"],
        "email": ["user1@test.com"],
        "first_name": ["John"],
        "last_name": ["Doe"],
        "enabled": ["yes"],
        "created_at": ["2024-03-20T12:00:00Z"],
        "updated_at": ["2024-03-20T12:00:00Z"],
        "last_login_at": ["2024-03-20T12:00:00Z"]
    })
    errors = SchemaValidator.validate_dataframe(name_combinations_df, "Users")
    assert not errors, "Should accept first_name + last_name instead of full_name"

    # Test datetime format validation
    invalid_datetime_df = pd.DataFrame({
        "user_id": ["U1"],
        "username": ["user1"],
        "email": ["user1@test.com"],
        "full_name": ["User One"],
        "enabled": ["yes"],
        "created_at": ["invalid_date"],  # Invalid datetime
        "updated_at": ["2024-03-20T12:00:00Z"],
        "last_login_at": ["2024-03-20T12:00:00Z"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_datetime_df, "Users")
    assert errors
    assert any("Invalid type for field created_at" in error for error in errors)

    # Test boolean field validation
    invalid_boolean_df = pd.DataFrame({
        "user_id": ["U1"],
        "username": ["user1"],
        "email": ["user1@test.com"],
        "full_name": ["User One"],
        "enabled": ["maybe"],  # Invalid boolean
        "created_at": ["2024-03-20T12:00:00Z"],
        "updated_at": ["2024-03-20T12:00:00Z"],
        "last_login_at": ["2024-03-20T12:00:00Z"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_boolean_df, "Users")
    assert errors
    assert any("Invalid boolean values" in error for error in errors)


def test_validate_groups_schema():
    """Test validation of Groups schema."""
    # Valid data with group_id
    valid_id_df = pd.DataFrame({
        "group_id": ["G1"],
        "group_name": ["Admins"],
        "description": ["Admin group"]
    })
    errors = SchemaValidator.validate_dataframe(valid_id_df, "Groups")
    assert not errors, f"Unexpected errors: {errors}"

    # Valid data with only group_name
    valid_name_df = pd.DataFrame({
        "group_name": ["Admins"],
        "description": ["Admin group"]
    })
    errors = SchemaValidator.validate_dataframe(valid_name_df, "Groups")
    assert not errors, "Should accept data with only group_name"

    # Test missing description
    invalid_desc_df = pd.DataFrame({
        "group_id": ["G1"],
        "group_name": ["Admins"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_desc_df, "Groups")
    assert errors
    assert any("Missing required field: description" in error for error in errors)


def test_validate_roles_schema():
    """Test validation of Roles schema."""
    # Valid data with role_id
    valid_id_df = pd.DataFrame({
        "role_id": ["R1"],
        "role_name": ["Admin"],
        "description": ["Administrator role"]
    })
    errors = SchemaValidator.validate_dataframe(valid_id_df, "Roles")
    assert not errors, f"Unexpected errors: {errors}"

    # Valid data with only role_name
    valid_name_df = pd.DataFrame({
        "role_name": ["Admin"],
        "description": ["Administrator role"]
    })
    errors = SchemaValidator.validate_dataframe(valid_name_df, "Roles")
    assert not errors, "Should accept data with only role_name"

    # Test missing description
    invalid_desc_df = pd.DataFrame({
        "role_id": ["R1"],
        "role_name": ["Admin"]
    })
    errors = SchemaValidator.validate_dataframe(invalid_desc_df, "Roles")
    assert errors
    assert any("Missing required field: description" in error for error in errors)


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
    
    # Test non-existent user references
    invalid_user_groups = pd.DataFrame({
        "user_id": ["U3"],  # Non-existent user
        "group_id": ["G1"]
    })
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, invalid_user_groups, valid_group_groups
    )
    assert errors
    assert any("Invalid user_ids" in error for error in errors)
    
    # Test non-existent group references
    invalid_group_groups = pd.DataFrame({
        "parent_group_id": ["G3"],  # Non-existent group
        "child_group_id": ["G1"]
    })
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, valid_user_groups, invalid_group_groups
    )
    assert errors
    assert any("Invalid parent_group_ids" in error for error in errors)
    
    # Test circular references
    circular_group_groups = pd.DataFrame({
        "parent_group_id": ["G1", "G2"],
        "child_group_id": ["G2", "G1"]
    })
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, valid_user_groups, circular_group_groups
    )
    assert errors
    assert any("Circular reference detected" in error for error in errors)

    # Test complex circular references
    complex_circular_groups = pd.DataFrame({
        "parent_group_id": ["G1", "G2", "G3"],
        "child_group_id": ["G2", "G3", "G1"]
    })
    errors = SchemaValidator.validate_relationships(
        users_df, groups_df, valid_user_groups, complex_circular_groups
    )
    assert errors
    assert any("Circular reference detected" in error for error in errors)


def test_validate_empty_dataframes():
    """Test validation of empty DataFrames."""
    empty_df = pd.DataFrame()
    for schema in ["Users", "Groups", "Roles"]:
        errors = SchemaValidator.validate_dataframe(empty_df, schema)
        assert errors
        assert any(f"DataFrame for {schema} is empty" in error for error in errors)


def test_validate_unknown_schema():
    """Test validation with unknown schema."""
    df = pd.DataFrame({"test": ["value"]})
    errors = SchemaValidator.validate_dataframe(df, "UnknownSchema")
    assert errors
    assert any("No schema defined for UnknownSchema" in error for error in errors) 