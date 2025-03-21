#!/usr/bin/env python3

"""Simple script to check Excel file contents."""

from pathlib import Path

from src.utils.excel_handler import ExcelHandler


def main():
    """Check Excel file contents."""
    input_file = Path("input/AD_Export_2025-03-20_1839.xlsx")

    if not input_file.exists():
        print(f"File not found: {input_file}")
        return

    try:
        # Use ExcelHandler to read sheets
        handler = ExcelHandler(input_file)
        sheets = handler.load_sheets()

        print("\nFound sheets:")
        for sheet_name in sheets:
            print(f"  - {sheet_name}")

        print("\nColumns in each sheet:")
        for sheet_name, df in sheets.items():
            print(f"\n{sheet_name}:")
            for col in df.columns:
                print(f"  - {col}")

    except Exception as e:
        print(f"Error reading file: {e}")


if __name__ == "__main__":
    main()
