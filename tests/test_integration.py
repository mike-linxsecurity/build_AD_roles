"""Integration tests for AD Role Mapping Tool."""

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from AD_oracle import main


@pytest.fixture
def sample_input_excel():
    """Create a sample input Excel file for testing."""
    with TemporaryDirectory() as temp_dir:
        # Create test data
        users_data = {
            "user_id": ["U1", "U2"],
            "username": ["user1", "user2"],
            "email": ["user1@test.com", "user2@test.com"],
            "full_name": ["User One", "User Two"],
            "enabled": ["yes", "yes"],
            "created_at": ["2024-03-20T12:00:00Z", "2024-03-20T12:00:00Z"],
            "updated_at": ["2024-03-20T12:00:00Z", "2024-03-20T12:00:00Z"],
            "last_login_at": ["2024-03-20T12:00:00Z", "2024-03-20T12:00:00Z"],
        }

        groups_data = {
            "group_id": ["G1", "G2"],
            "group_name": ["Administrators", "Users"],
            "description": ["Admin Group", "Regular Users"],
        }

        user_groups_data = {"user_id": ["U1", "U2"], "group_id": ["G1", "G2"]}

        group_groups_data = {"parent_group_id": ["G1"], "child_group_id": ["G2"]}

        roles_data = {
            "role_id": ["R_Administrators", "R_Users"],
            "role_name": ["Administrators", "Users"],
            "description": ["Role for Administrators", "Role for Users"],
        }

        user_roles_data = {
            "user_id": ["U1", "U2"],
            "role_id": ["R_Administrators", "R_Users"],
        }

        group_roles_data = {
            "group_id": ["G1", "G2"],
            "role_id": ["R_Administrators", "R_Users"],
        }

        # Create Excel file
        file_path = Path(temp_dir) / "test_input.xlsx"
        with pd.ExcelWriter(file_path) as writer:
            pd.DataFrame(users_data).to_excel(writer, sheet_name="Users", index=False)
            pd.DataFrame(groups_data).to_excel(writer, sheet_name="Groups", index=False)
            pd.DataFrame(user_groups_data).to_excel(
                writer, sheet_name="User_Groups", index=False
            )
            pd.DataFrame(group_groups_data).to_excel(
                writer, sheet_name="Group_Groups", index=False
            )
            pd.DataFrame(roles_data).to_excel(writer, sheet_name="Roles", index=False)
            pd.DataFrame(user_roles_data).to_excel(
                writer, sheet_name="User_Roles", index=False
            )
            pd.DataFrame(group_roles_data).to_excel(
                writer, sheet_name="Group_Roles", index=False
            )

        # Create builtin groups file
        builtin_groups = {
            "BuiltIn_AD_Groups": ["Domain Admins"],
            "Original_Role_Groups": ["Administrators", "Users"],
            "Exchange_Server_Groups": ["Exchange Admins"],
        }
        builtin_groups_path = Path(temp_dir) / "builtin_groups.json"
        with open(builtin_groups_path, "w") as f:
            json.dump(builtin_groups, f)

        yield file_path


def test_end_to_end_processing(
    monkeypatch, tmp_path, sample_input_excel, sample_builtin_groups
):
    """Test end-to-end processing of AD data."""
    output_file = tmp_path / "output.xlsx"

    # Set up command line arguments
    test_args = [
        "AD_oracle.py",
        "--input",
        str(sample_input_excel),
        "--output",
        str(output_file),
        "--builtin-groups",
        str(sample_builtin_groups),
        "--log-level",
        "INFO",
    ]
    monkeypatch.setattr("sys.argv", test_args)

    # Run the main function
    result = main()
    assert result == 0
    assert output_file.exists()

    # Verify output file structure
    output_sheets = pd.read_excel(output_file, sheet_name=None)
    required_sheets = {
        "Users",
        "Groups",
        "User_Groups",
        "Group_Groups",
        "Roles",
        "User_Roles",
        "Group_Roles",
    }
    assert set(output_sheets.keys()) == required_sheets

    # Verify population rules for Users sheet
    users_df = output_sheets["Users"]
    assert not users_df.empty

    # Verify user identification fields population
    for _, row in users_df.iterrows():
        # At least one identifier must be present
        assert any(pd.notna(row[field]) for field in ["user_id", "username", "email"])

        # If user_id is missing, it should be populated from email or username
        if pd.isna(row["user_id"]):
            assert pd.notna(row["email"]) or pd.notna(row["username"])

        # If username is missing, it should be populated from email
        if pd.isna(row["username"]) and pd.notna(row["email"]):
            assert "@" in str(row["email"])

    # Verify name fields population
    for _, row in users_df.iterrows():
        # Either full_name or both first_name and last_name must be present
        has_full_name = pd.notna(row.get("full_name", None))
        has_first_last = pd.notna(row.get("first_name", None)) and pd.notna(
            row.get("last_name", None)
        )
        assert has_full_name or has_first_last, "Missing required name fields"

    # Verify Groups sheet population rules
    groups_df = output_sheets["Groups"]
    assert not groups_df.empty

    for _, row in groups_df.iterrows():
        # At least one of group_id or group_name must be present
        assert pd.notna(row["group_id"]) or pd.notna(row["group_name"])

        # Description must be present with group_name
        if pd.notna(row["group_name"]):
            assert pd.notna(row["description"])

        # If description is missing, it should be populated from group_name
        if pd.isna(row["description"]) and pd.notna(row["group_name"]):
            assert row["description"] == row["group_name"]

    # Verify Roles sheet population rules
    roles_df = output_sheets["Roles"]
    assert not roles_df.empty

    for _, row in roles_df.iterrows():
        # At least one of role_id or role_name must be present
        assert pd.notna(row["role_id"]) or pd.notna(row["role_name"])

        # If role_id is missing, it should use role_name
        if pd.isna(row["role_id"]) and pd.notna(row["role_name"]):
            assert row["role_id"] == row["role_name"]

    # Verify User_Groups relationships
    user_groups_df = output_sheets["User_Groups"]
    if not user_groups_df.empty:
        for _, row in user_groups_df.iterrows():
            # Both user_id and group_id must be populated
            assert pd.notna(row["user_id"])
            assert pd.notna(row["group_id"])

            # Verify user_id exists in Users sheet
            assert row["user_id"] in users_df["user_id"].values

            # Verify group_id exists in Groups sheet
            assert row["group_id"] in groups_df["group_id"].values

    # Verify Group_Groups relationships
    group_groups_df = output_sheets["Group_Groups"]
    if not group_groups_df.empty:
        for _, row in group_groups_df.iterrows():
            # Both parent_group_id and child_group_id must be populated
            assert pd.notna(row["parent_group_id"])
            assert pd.notna(row["child_group_id"])

            # Verify both groups exist in Groups sheet
            assert row["parent_group_id"] in groups_df["group_id"].values
            assert row["child_group_id"] in groups_df["group_id"].values

    # Verify User_Roles relationships
    user_roles_df = output_sheets["User_Roles"]
    if not user_roles_df.empty:
        for _, row in user_roles_df.iterrows():
            # Both user_id and role_id must be populated
            assert pd.notna(row["user_id"])
            assert pd.notna(row["role_id"])

            # Verify user_id exists in Users sheet
            assert row["user_id"] in users_df["user_id"].values

            # Verify role_id exists in Roles sheet
            assert row["role_id"] in roles_df["role_id"].values

    # Verify Group_Roles relationships
    group_roles_df = output_sheets["Group_Roles"]
    if not group_roles_df.empty:
        for _, row in group_roles_df.iterrows():
            # Both group_id and role_id must be populated
            assert pd.notna(row["group_id"])
            assert pd.notna(row["role_id"])

            # Verify group_id exists in Groups sheet
            assert row["group_id"] in groups_df["group_id"].values

            # Verify role_id exists in Roles sheet
            assert row["role_id"] in roles_df["role_id"].values


def test_error_handling(monkeypatch, tmp_path):
    """Test error handling in main script."""
    # Test with non-existent input file
    test_args = [
        "AD_oracle.py",
        "--input",
        "nonexistent.xlsx",
        "--output",
        str(tmp_path / "output.xlsx"),
        "--log-level",
        "ERROR",
    ]
    monkeypatch.setattr("sys.argv", test_args)

    result = main()
    assert result == 1  # Should fail gracefully


def test_invalid_input_data(
    monkeypatch, tmp_path, sample_input_excel, sample_builtin_groups
):
    """Test processing of invalid input data."""
    # Create invalid input file
    invalid_input = tmp_path / "invalid_input.xlsx"

    # Create Excel file with missing required columns
    invalid_users_df = pd.DataFrame({"username": ["user1"]})  # Missing required fields

    with pd.ExcelWriter(invalid_input) as writer:
        invalid_users_df.to_excel(writer, sheet_name="Users", index=False)
        # Missing other required sheets

    test_args = [
        "AD_oracle.py",
        "--input",
        str(invalid_input),
        "--output",
        str(tmp_path / "output.xlsx"),
        "--builtin-groups",
        str(sample_builtin_groups),
        "--log-level",
        "ERROR",
    ]
    monkeypatch.setattr("sys.argv", test_args)

    result = main()
    assert result == 1  # Should fail due to validation errors
