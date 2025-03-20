"""Common test fixtures for AD Role Mapping Tool."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def test_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_input_excel(test_data_dir):
    """Create a sample input Excel file with test data."""
    file_path = test_data_dir / "test_input.xlsx"
    
    # Sample user data
    users_df = pd.DataFrame({
        "user_id": ["U1", "U2"],
        "username": ["user1", "user2"],
        "email": ["user1@test.com", "user2@test.com"],
        "full_name": ["User One", "User Two"],
        "enabled": ["yes", "yes"]
    })
    
    # Sample group data
    groups_df = pd.DataFrame({
        "group_id": ["G1", "G2"],
        "group_name": ["Administrators", "Users"],
        "description": ["Admin Group", "Regular Users"]
    })
    
    # Sample user-group relationships
    user_groups_df = pd.DataFrame({
        "user_id": ["U1", "U2"],
        "group_id": ["G1", "G2"]
    })
    
    # Sample group-group relationships
    group_groups_df = pd.DataFrame({
        "parent_group_id": ["G1"],
        "child_group_id": ["G2"]
    })
    
    # Create Excel writer object
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        users_df.to_excel(writer, sheet_name='Users', index=False)
        groups_df.to_excel(writer, sheet_name='Groups', index=False)
        user_groups_df.to_excel(writer, sheet_name='User_Groups', index=False)
        group_groups_df.to_excel(writer, sheet_name='Group_Groups', index=False)
    
    return file_path


@pytest.fixture
def sample_builtin_groups(test_data_dir):
    """Create a sample builtin_groups.json file."""
    file_path = test_data_dir / "builtin_groups.json"
    content = {
        "BuiltIn_AD_Groups": ["Domain Admins"],
        "Original_Role_Groups": ["Administrators", "Users"],
        "Exchange_Server_Groups": ["Exchange Admins"]
    }
    
    import json
    with open(file_path, 'w') as f:
        json.dump(content, f, indent=2)
    
    return file_path 