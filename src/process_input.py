#!/usr/bin/env python3
"""Process AD export file and generate role mappings.

This script reads an AD export Excel file from the input directory,
validates its contents, and generates role mappings in the output directory.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Union

import pandas as pd

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.excel_handler import ExcelHandler
from src.utils.schema_validator import SchemaValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def process_input_file(input_file: Union[str, Path]) -> Dict[str, pd.DataFrame]:
    """Process and validate input Excel file.

    Args:
        input_file: Path to the input Excel file containing AD data

    Returns:
        Dict containing validated DataFrames for each sheet

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If input data is invalid
    """
    # Ensure input file exists
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Read input data
    excel = ExcelHandler()
    sheets = excel.read_sheets(input_file)

    # Validate data against schema
    validator = SchemaValidator()
    errors = validator.validate_sheets(sheets)
    if errors:
        raise ValueError("Error validating input data: " + "; ".join(errors))

    return sheets


def main():
    """Main function to process AD export file."""
    try:
        # Get the input file
        input_dir = project_root / "input"
        excel_files = list(input_dir.glob("*.xlsx"))

        if not excel_files:
            logger.error("No Excel files found in input directory")
            sys.exit(1)

        input_file = excel_files[0]  # Process the first Excel file found
        logger.info(f"Processing input file: {input_file}")

        # Initialize handlers
        excel_handler = ExcelHandler(input_file)
        validator = SchemaValidator()

        # Read and validate sheets
        sheets = excel_handler.read_sheets()
        logger.info("Successfully read input sheets")

        # Validate each sheet's schema
        for sheet_name, df in sheets.items():
            errors = validator.validate_dataframe(df, sheet_name)
            if errors:
                logger.error(f"Validation errors in {sheet_name}:")
                for error in errors:
                    logger.error(f"  - {error}")
                sys.exit(1)

        # Validate relationships
        relationship_errors = validator.validate_relationships(
            sheets["Users"],
            sheets["Groups"],
            sheets["User_Groups"],
            sheets["Group_Groups"],
        )
        if relationship_errors:
            logger.error("Relationship validation errors:")
            for error in relationship_errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        # Create output directory if it doesn't exist
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)

        # Write output file with validated data
        output_file = output_dir / f"AD_Roles_{input_file.stem}.xlsx"
        excel_handler.write_output(output_file, sheets)
        logger.info(f"Successfully wrote output to: {output_file}")

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
