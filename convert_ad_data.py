#!/usr/bin/env python3

"""Process Active Directory export files from input directory to output directory."""

import sys
from pathlib import Path

from src.AD_oracle import process_ad_data


def main():
    """Process AD data files from input directory and save results to output."""
    try:
        # Get input directory
        input_dir = Path("input")
        output_dir = Path("output")
        builtin_groups_file = Path("src/builtin_groups.json")

        # Ensure directories exist
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        # Check if builtin_groups.json exists
        if not builtin_groups_file.exists():
            print("❌ Required file src/builtin_groups.json not found.")
            sys.exit(1)

        # Find Excel files in input directory
        excel_files = list(input_dir.glob("*.xlsx"))

        if not excel_files:
            print("❌ No Excel files found in input directory.")
            print("Please place your AD export files in the 'input' directory.")
            sys.exit(1)

        # Process each Excel file
        for excel_file in excel_files:
            output_file = output_dir / f"processed_{excel_file.name}"
            print(f"\n🔄 Processing {excel_file.name}...")
            process_ad_data(str(excel_file), str(output_file), str(builtin_groups_file))
            print(f"✅ Output saved to: {output_file}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
