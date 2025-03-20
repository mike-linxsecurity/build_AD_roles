# AD Role Mapping Tool

A Python tool for processing Active Directory (AD) data and generating role-based relationships by mapping predefined AD groups to roles.

## Overview

This tool takes an input Excel file containing AD data (Users, Groups, User-Group relationships, and Group-Group relationships) and generates a structured output that maps these entities to roles based on predefined AD group definitions. The tool preserves original role group hierarchies and unrolls nested group relationships to create comprehensive role assignments for both users and groups.

## Features

- Processes structured AD data from Excel input files
- Maps predefined AD groups to roles using builtin group definitions
- Handles nested group relationships
- Generates role assignments for both users and groups
- Maintains data integrity and relationship hierarchies
- Provides detailed output in Excel format conforming to specified schema

## Requirements

- Python 3.8+
- Required Python packages (installed automatically via init.sh):
  - pandas
  - openpyxl
  - pyyaml
  - python-dotenv

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd build_AD_roles
```

2. Run the initialization script:
```bash
./init.sh
```

This will set up the Python virtual environment and install all required dependencies.

## Usage

1. Place your input Excel file (generated from AD_Export.ps1) in the `input/` directory.

2. Run the tool:
```bash
python src/AD_oracle.py --input input/your_input_file.xlsx --output output/roles_output.xlsx
```

## Input Format

The input Excel file should contain the following sheets:
- Users: User details (user_id, username, email, etc.)
- Groups: Group details (group_id, group_name, description)
- User_Groups: User-to-group mappings
- Group_Groups: Nested group relationships

## Output Format

The tool generates an Excel file with the following sheets:
- Users: Original user data (unchanged)
- Groups: Original group data (unchanged)
- Roles: Mapped roles from predefined AD groups
- User_Groups: Original user-group mappings (unchanged)
- Group_Groups: Original group-group mappings (unchanged)
- User_Roles: Generated user-to-role mappings
- Group_Roles: Generated group-to-role mappings

## Configuration

The tool uses two main configuration files:
- `builtin_groups.json`: Defines the predefined AD groups and their role mappings
- `.env`: Contains environment-specific configurations (created during initialization)

## Project Structure

```
build_AD_roles/
├── src/
│   ├── AD_oracle.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── excel_handler.py
│   │   ├── role_mapper.py
│   │   └── group_resolver.py
├── tests/
│   ├── __init__.py
│   ├── test_role_mapper.py
│   ├── test_group_resolver.py
│   └── test_excel_handler.py
├── input/
├── output/
├── notes/
├── .env
├── .gitignore
├── init.sh
├── requirements.txt
└── README.md
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. These are set up automatically by init.sh.

## Error Handling

The tool includes comprehensive error handling for:
- Missing or malformed input files
- Schema validation errors
- Data integrity issues
- Output generation failures

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[License Type] - See LICENSE file for details

## Support

For support, please [contact information or process] 