"""Tests for schema validation utilities."""

import pandas as pd
import pytest

from src.utils.schema_validator import SchemaValidator


@pytest.fixture
def schema_validator():
    """Create SchemaValidator instance for testing."""
    return SchemaValidator()


def test_validate_users_schema(schema_validator):
    """Test validation of Users schema."""
    # Valid data
    valid_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "username": ["user1"],
            "email": ["user1@test.com"],
            "full_name": ["User One"],
            "enabled": ["yes"],
            "created_at": ["2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z"],
        }
    )
    errors = schema_validator.validate_dataframe(valid_df, "Users")
    assert not errors

    # Invalid data - missing required fields
    invalid_df = pd.DataFrame({"username": ["user1"]})
    errors = schema_validator.validate_dataframe(invalid_df, "Users")
    assert len(errors) > 0


def test_validate_groups_schema(schema_validator):
    """Test validation of Groups schema."""
    # Valid data with group_id
    valid_id_df = pd.DataFrame(
        {"group_id": ["G1"], "group_name": ["Admins"], "description": ["Admin group"]}
    )
    errors = schema_validator.validate_dataframe(valid_id_df, "Groups")
    assert not errors

    # Valid data with group_name only
    valid_name_df = pd.DataFrame(
        {"group_name": ["Users"], "description": ["Regular users"]}
    )
    errors = schema_validator.validate_dataframe(valid_name_df, "Groups")
    assert not errors

    # Invalid data - missing both identifiers
    invalid_df = pd.DataFrame({"description": ["Invalid group"]})
    errors = schema_validator.validate_dataframe(invalid_df, "Groups")
    assert len(errors) > 0


def test_validate_roles_schema(schema_validator):
    """Test validation of Roles schema."""
    # Valid data with role_id
    valid_id_df = pd.DataFrame(
        {
            "role_id": ["R1"],
            "role_name": ["Admin"],
            "description": ["Administrator role"],
        }
    )
    errors = schema_validator.validate_dataframe(valid_id_df, "Roles")
    assert not errors

    # Valid data with role_name only
    valid_name_df = pd.DataFrame(
        {"role_name": ["User"], "description": ["Regular user role"]}
    )
    errors = schema_validator.validate_dataframe(valid_name_df, "Roles")
    assert not errors

    # Invalid data - missing both identifiers
    invalid_df = pd.DataFrame({"description": ["Invalid role"]})
    errors = schema_validator.validate_dataframe(invalid_df, "Roles")
    assert len(errors) > 0


def test_validate_relationships(schema_validator):
    """Test validation of relationships between entities."""
    users_df = pd.DataFrame({"user_id": ["U1", "U2"], "username": ["user1", "user2"]})

    groups_df = pd.DataFrame(
        {"group_id": ["G1", "G2"], "group_name": ["Group1", "Group2"]}
    )

    # Valid relationships
    valid_user_groups = pd.DataFrame({"user_id": ["U1"], "group_id": ["G1"]})

    valid_group_groups = pd.DataFrame(
        {"parent_group_id": ["G1"], "child_group_id": ["G2"]}
    )

    errors = schema_validator.validate_relationships(
        users_df=users_df,
        groups_df=groups_df,
        user_groups_df=valid_user_groups,
        group_groups_df=valid_group_groups,
    )
    assert not errors

    # Invalid relationships - non-existent user
    invalid_user_groups = pd.DataFrame(
        {"user_id": ["U3"], "group_id": ["G1"]}  # Non-existent user
    )

    errors = schema_validator.validate_relationships(
        users_df=users_df,
        groups_df=groups_df,
        user_groups_df=invalid_user_groups,
        group_groups_df=valid_group_groups,
    )
    assert len(errors) > 0

    # Invalid relationships - non-existent group
    invalid_group_groups = pd.DataFrame(
        {"parent_group_id": ["G3"], "child_group_id": ["G1"]}  # Non-existent group
    )

    errors = schema_validator.validate_relationships(
        users_df=users_df,
        groups_df=groups_df,
        user_groups_df=valid_user_groups,
        group_groups_df=invalid_group_groups,
    )
    assert len(errors) > 0


def test_validate_empty_dataframes(schema_validator):
    """Test validation of empty DataFrames."""
    empty_df = pd.DataFrame()
    for schema in ["Users", "Groups", "Roles"]:
        errors = schema_validator.validate_dataframe(empty_df, schema)
        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)


def test_validate_unknown_schema(schema_validator):
    """Test validation with unknown schema."""
    df = pd.DataFrame({"test": ["value"]})
    errors = schema_validator.validate_dataframe(df, "UnknownSchema")
    assert len(errors) > 0
    assert any("unknown" in error.lower() for error in errors)
