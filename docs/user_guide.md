# AD Role Mapping Tool - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Data Preparation](#data-preparation)
4. [Running the Tool](#running-the-tool)
5. [Understanding Output](#understanding-output)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Introduction

The AD Role Mapping Tool is designed to process Active Directory (AD) data and generate role-based relationships by mapping predefined AD groups to roles. This guide will walk you through the setup process, data preparation, and usage of the tool.

## Installation

### Prerequisites
- Python 3.8 or higher
- Git (optional, for version control)
- Excel file with AD export data

### Setup Steps

1. Get the tool:
   ```bash
   git clone [repository-url]
   cd build_AD_roles
   ```

2. Run the initialization script:
   ```bash
   ./init.sh
   ```

   Note: If you're a developer or want to run tests, use:
   ```bash
   ./init.sh -t
   ```

3. Verify installation:
   ```bash
   python src/AD_oracle.py --help
   ```

## Data Preparation

### Input Excel File Requirements

Your input Excel file must contain these sheets:

#### 1. Users Sheet
Required columns:
- `user_id`: AD ObjectGUID
- `username`: AD SamAccountName
- `email`: AD EmailAddress

Optional columns:
- `full_name`: AD DisplayName
- `first_name`: AD GivenName
- `last_name`: AD Surname
- `enabled`: AD Enabled status (true/false)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `last_login_at`: Last login timestamp

Date format: ISO 8601 (e.g., "2024-03-20T12:00:00Z")

#### 2. Groups Sheet
Required columns:
- `group_id`: AD ObjectGUID
- `group_name`: AD Name

Optional columns:
- `description`: AD Description

#### 3. User_Groups Sheet
Required columns:
- `user_id`: User's AD ObjectGUID
- `group_id`: Group's AD ObjectGUID

#### 4. Group_Groups Sheet
Required columns:
- `parent_group_id`: Parent group's AD ObjectGUID
- `child_group_id`: Child group's AD ObjectGUID

### Data Validation Rules

1. User Identification:
   - At least one of: user_id, username, or email must be present
   - Missing user_id will be populated from email or username

2. Name Fields:
   - Either full_name OR (first_name + last_name) must be present
   - Output will contain all three fields

3. Group Identification:
   - At least one of: group_id or group_name must be present
   - Missing group_id will be assigned an incrementing number

4. Relationships:
   - All referenced user_ids must exist in Users sheet
   - All referenced group_ids must exist in Groups sheet
   - No circular references in Group_Groups relationships

## Running the Tool

### Basic Usage

```bash
python src/AD_oracle.py \
    --input input/ad_export.xlsx \
    --output output/role_mappings.xlsx
```

### Advanced Options

1. Custom builtin groups configuration:
   ```bash
   python src/AD_oracle.py \
       --input input/ad_export.xlsx \
       --output output/role_mappings.xlsx \
       --builtin-groups config/custom_groups.json
   ```

2. Debug logging:
   ```bash
   python src/AD_oracle.py \
       --input input/ad_export.xlsx \
       --output output/role_mappings.xlsx \
       --log-level DEBUG
   ```

### Command Line Arguments

- `--input`: Path to input Excel file (required)
- `--output`: Path to output Excel file (required)
- `--builtin-groups`: Path to custom builtin groups JSON (optional)
- `--log-level`: Logging level (optional, default: INFO)

## Understanding Output

### Output Excel File Structure

1. Original Data (unchanged):
   - Users sheet
   - Groups sheet
   - User_Groups sheet
   - Group_Groups sheet

2. Generated Data:
   - Roles sheet:
     - role_id: Unique identifier
     - role_name: Role name
     - description: Role description
     - source: Category from builtin_groups.json

   - User_Roles sheet:
     - user_id: User identifier
     - role_id: Role identifier

   - Group_Roles sheet:
     - group_id: Group identifier
     - role_id: Role identifier

### Role Mapping Rules

1. Role Priority:
   - Original_Role_Groups take precedence
   - Groups can only map to one role
   - First matching category is used

2. Role Inheritance:
   - Users inherit roles from their groups
   - Groups inherit roles from parent groups
   - Duplicate roles are removed

## Configuration

### Environment Variables (.env)

```ini
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Excel file limits
EXCEL_MAX_ROWS=1000000
EXCEL_MAX_COLS=16384
```

### Builtin Groups (builtin_groups.json)

```json
{
    "Original_Role_Groups": [
        "Administrators",
        "PowerUsers"
    ],
    "Additional_Role_Groups": [
        "Developers",
        "Analysts"
    ]
}
```

Categories are processed in order of appearance.

## Troubleshooting

### Common Issues

1. Missing Required Columns
   ```
   Error: Missing required column 'user_id' in Users sheet
   Solution: Ensure all required columns are present in input file
   ```

2. Invalid Data Format
   ```
   Error: Invalid datetime format in 'created_at'
   Solution: Use ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
   ```

3. Circular Dependencies
   ```
   Error: Circular dependency detected in Group_Groups
   Solution: Remove circular references in group relationships
   ```

4. File Access Issues
   ```
   Error: Permission denied when writing output file
   Solution: Ensure write permissions for output directory
   ```

### Debug Mode

Run with debug logging for detailed information:
```bash
python src/AD_oracle.py --input in.xlsx --output out.xlsx --log-level DEBUG
```

### Validation Steps

1. Check input file format
2. Verify required columns
3. Validate data types
4. Check relationship integrity
5. Verify output permissions

## Best Practices

1. Data Preparation:
   - Clean and validate data before processing
   - Remove duplicate entries
   - Ensure consistent date formats
   - Verify group relationships

2. Configuration:
   - Keep builtin_groups.json updated
   - Use meaningful role names
   - Document custom configurations

3. Operation:
   - Regular backups of input/output files
   - Test with sample data first
   - Monitor log files for issues
   - Use version control for configurations

4. Maintenance:
   - Regular updates to builtin groups
   - Periodic validation of role mappings
   - Clean up old output files
   - Document custom modifications
```
