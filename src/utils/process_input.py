"""Process input data for AD Role Mapping Tool."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from .excel_handler import ExcelHandler
from .role_mapper import RoleMapper
from .schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


def process_input(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    builtin_groups_file: Union[str, Path] = "config/builtin_groups.json",
) -> None:
    """Process input data and generate output files.

    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file
        builtin_groups_file: Path to builtin groups JSON file
    """
    logger.info(f"Processing input file: {input_file}")

    # Initialize handlers
    excel_handler = ExcelHandler(file_path=input_file)
    schema_validator = SchemaValidator()

    # Read input data
    input_data = excel_handler.read_sheets(input_file)
    logger.info(f"Found sheets: {list(input_data.keys())}")

    # Validate input data
    users_df = input_data.get("Users", pd.DataFrame())
    groups_df = input_data.get("Groups", pd.DataFrame())
    user_groups_df = input_data.get("User_Groups", pd.DataFrame())
    group_groups_df = input_data.get("Group_Groups", pd.DataFrame())

    # Log input data shapes
    logger.debug(f"Users shape: {users_df.shape}")
    logger.debug(f"Groups shape: {groups_df.shape}")
    logger.debug(f"User_Groups shape: {user_groups_df.shape}")
    logger.debug(f"Group_Groups shape: {group_groups_df.shape}")

    # Validate schemas
    validation_errors = []
    validation_errors.extend(schema_validator.validate_dataframe(users_df, "Users"))
    validation_errors.extend(schema_validator.validate_dataframe(groups_df, "Groups"))
    validation_errors.extend(
        schema_validator.validate_dataframe(user_groups_df, "User_Groups")
    )
    validation_errors.extend(
        schema_validator.validate_dataframe(group_groups_df, "Group_Groups")
    )

    if validation_errors:
        logger.error("Schema validation errors:")
        for error in validation_errors:
            logger.error(error)
        raise ValueError("Schema validation failed")

    # Create role mappings from groups
    role_mapper = RoleMapper(builtin_groups_file=str(builtin_groups_file))
    role_mappings = role_mapper.create_role_mappings(groups_df)
    roles_df = role_mappings["Roles"]
    group_roles_df = role_mappings["Group_Roles"]
    logger.info(
        f"Created {len(roles_df)} roles and {len(group_roles_df)} group-role mappings"
    )
    logger.debug(f"Initial group-role mappings:\n{group_roles_df}")

    # Resolve additional group-role relationships through inheritance
    resolved_group_roles_df = role_mapper.resolve_group_roles(
        roles_df=roles_df,
        group_groups_df=group_groups_df,
        groups_df=groups_df,
        group_roles_df=group_roles_df,
    )
    logger.debug(f"Resolved group-role mappings:\n{resolved_group_roles_df}")

    # Ensure we have the correct columns in resolved_group_roles_df
    if not resolved_group_roles_df.empty:
        resolved_group_roles_df = resolved_group_roles_df[["group_id", "role_id"]]
        resolved_group_roles_df["group_id"] = resolved_group_roles_df[
            "group_id"
        ].astype(str)
        resolved_group_roles_df["role_id"] = resolved_group_roles_df["role_id"].astype(
            str
        )
        logger.debug(f"Processed group-role mappings:\n{resolved_group_roles_df}")

    # Resolve user-role relationships using resolved group roles
    user_roles_df = role_mapper.resolve_user_roles(
        user_groups_df=user_groups_df, group_roles_df=resolved_group_roles_df
    )
    logger.info(f"Resolved {len(user_roles_df)} user-role relationships")
    logger.debug(f"User-role mappings:\n{user_roles_df}")

    # Ensure we have the correct columns in user_roles_df
    if not user_roles_df.empty:
        user_roles_df = user_roles_df[["user_id", "role_id"]]
        user_roles_df["user_id"] = user_roles_df["user_id"].astype(str)
        user_roles_df["role_id"] = user_roles_df["role_id"].astype(str)
        logger.debug(f"Processed user-role mappings:\n{user_roles_df}")

    # Prepare output data
    output_data = {
        "Users": users_df,
        "Groups": groups_df,
        "Roles": roles_df,
        "User_Groups": user_groups_df,
        "Group_Groups": group_groups_df,
        "User_Roles": user_roles_df,
        "Group_Roles": resolved_group_roles_df,  # Use resolved group roles
    }

    # Write output data
    excel_handler.save_sheets(output_data, output_file)
    logger.info(f"Output written to {output_file}")

    # Print summary
    print("\n✨ AD Role Mapping Complete!\n")
    print("📊 Summary:")
    print(f"  • Users processed: {len(users_df)}")
    print(f"  • Groups processed: {len(groups_df)}")
    print(f"  • Roles created: {len(roles_df)}")
    print(f"  • Group-role mappings: {len(resolved_group_roles_df)}")
    print(f"  • User-role mappings: {len(user_roles_df)}")
    print(f"\n📁 Output file: {output_file}")
    print("✅ Conversion completed successfully!")
    print("Check the 'output' directory for processed files.")
