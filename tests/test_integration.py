"""Integration tests for AD Role Mapping Tool."""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from AD_oracle import main


def test_end_to_end_processing(monkeypatch, tmp_path, sample_input_excel, sample_builtin_groups):
    """Test end-to-end processing of AD data."""
    output_file = tmp_path / "output.xlsx"
    
    # Set up command line arguments
    test_args = [
        "AD_oracle.py",
        "--input", str(sample_input_excel),
        "--output", str(output_file),
        "--builtin-groups", str(sample_builtin_groups),
        "--log-level", "INFO"
    ]
    monkeypatch.setattr("sys.argv", test_args)
    
    # Run the main function
    result = main()
    assert result == 0
    assert output_file.exists()
    
    # Verify output file structure
    output_sheets = pd.read_excel(output_file, sheet_name=None)
    required_sheets = {
        "Users", "Groups", "User_Groups", "Group_Groups",
        "Roles", "User_Roles", "Group_Roles"
    }
    assert set(output_sheets.keys()) == required_sheets
    
    # Verify role mappings
    roles_df = output_sheets["Roles"]
    assert not roles_df.empty
    assert all(col in roles_df.columns for col in ["role_id", "role_name", "description"])
    
    # Verify user role assignments
    user_roles_df = output_sheets["User_Roles"]
    assert not user_roles_df.empty
    assert all(col in user_roles_df.columns for col in ["user_id", "role_id"])
    
    # Verify group role assignments
    group_roles_df = output_sheets["Group_Roles"]
    assert not group_roles_df.empty
    assert all(col in group_roles_df.columns for col in ["group_id", "role_id"])


def test_error_handling(monkeypatch, tmp_path):
    """Test error handling in main script."""
    # Test with non-existent input file
    test_args = [
        "AD_oracle.py",
        "--input", "nonexistent.xlsx",
        "--output", str(tmp_path / "output.xlsx"),
        "--log-level", "ERROR"
    ]
    monkeypatch.setattr("sys.argv", test_args)
    
    result = main()
    assert result == 1  # Should fail gracefully


def test_invalid_input_data(monkeypatch, tmp_path, sample_input_excel, sample_builtin_groups):
    """Test processing of invalid input data."""
    # Create invalid input file
    invalid_input = tmp_path / "invalid_input.xlsx"
    
    # Create Excel file with missing required columns
    invalid_users_df = pd.DataFrame({
        "username": ["user1"]  # Missing required fields
    })
    
    with pd.ExcelWriter(invalid_input) as writer:
        invalid_users_df.to_excel(writer, sheet_name="Users", index=False)
        # Missing other required sheets
    
    test_args = [
        "AD_oracle.py",
        "--input", str(invalid_input),
        "--output", str(tmp_path / "output.xlsx"),
        "--builtin-groups", str(sample_builtin_groups),
        "--log-level", "ERROR"
    ]
    monkeypatch.setattr("sys.argv", test_args)
    
    result = main()
    assert result == 1  # Should fail due to validation errors 