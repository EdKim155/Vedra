#!/usr/bin/env python3
"""
Script to setup sheets structure in an existing Google Spreadsheet.

This script adds all required sheets with proper structure to an existing spreadsheet.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

# Import sheet structures from create_sheets_template.py
sys.path.insert(0, str(project_root / "scripts"))
from create_sheets_template import SHEET_STRUCTURES, format_header_row, add_data_validation


def setup_sheets(spreadsheet_id: str, credentials_path: str) -> None:
    """Setup all sheets in existing spreadsheet."""

    print("=" * 70)
    print("Setting up Google Sheets Structure")
    print("=" * 70)

    # Authenticate
    print(f"\nAuthenticating with credentials from: {credentials_path}")
    credentials_path = Path(credentials_path)
    if not credentials_path.exists():
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(
        str(credentials_path),
        scopes=scopes,
    )

    client = gspread.authorize(creds)

    # Open spreadsheet
    print(f"\nOpening spreadsheet: {spreadsheet_id}")
    spreadsheet = client.open_by_key(spreadsheet_id)
    print(f"✓ Spreadsheet opened: {spreadsheet.title}")
    print(f"  URL: {spreadsheet.url}")

    # Get existing sheet names
    existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
    print(f"\nExisting sheets: {existing_sheets}")

    # Create required sheets
    print("\nCreating/updating sheets:")
    for sheet_name, structure in SHEET_STRUCTURES.items():
        print(f"\n  Processing: {sheet_name}")

        # Check if sheet exists
        if sheet_name in existing_sheets:
            print(f"    Sheet already exists, using existing")
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            print(f"    Creating new sheet")
            worksheet = spreadsheet.add_worksheet(
                title=sheet_name,
                rows=1000,
                cols=len(structure["headers"]),
            )

        # Clear existing content
        print(f"    Clearing existing data")
        worksheet.clear()

        # Add headers
        print(f"    Adding headers")
        worksheet.update(values=[structure["headers"]], range_name="A1")

        # Format header row
        print(f"    Formatting headers")
        try:
            format_header_row(worksheet)
        except Exception as e:
            print(f"    Warning: Could not format headers: {e}")

        # Add data validation - skip for now due to API issues
        # if "validations" in structure:
        #     print(f"    Adding data validation")
        #     add_data_validation(worksheet, structure["validations"])

        # Add example data
        if "examples" in structure:
            print(f"    Adding example data")
            for row_num, row_data in structure["examples"].items():
                cell_range = f"A{row_num + 1}"
                worksheet.update(values=[row_data], range_name=cell_range)

        # Resize columns
        print(f"    Adjusting column widths")
        for i in range(len(structure["headers"])):
            try:
                worksheet.columns_auto_resize(i, i)
            except:
                pass  # Some columns may fail to resize

        print(f"    ✓ Sheet '{sheet_name}' configured successfully")

    # Remove default Sheet1 if it exists and is empty
    try:
        sheet1 = spreadsheet.worksheet("Sheet1")
        if sheet1.row_count <= 1000 and not sheet1.get_all_values():
            spreadsheet.del_worksheet(sheet1)
            print("\n  ✓ Removed default 'Sheet1'")
    except:
        pass

    print("\n" + "=" * 70)
    print("✓ Sheets structure setup completed!")
    print("=" * 70)
    print(f"\nSpreadsheet URL: {spreadsheet.url}")
    print("\nSheets configured:")
    for sheet_name in SHEET_STRUCTURES.keys():
        print(f"  ✓ {sheet_name}")


def main() -> None:
    """Main function."""
    # Get configuration from environment
    credentials_path = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/southern-camera-476019-f1-416755b5d8b7.json"
    )
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_ID environment variable not set!")
        print("Set it in .env file")
        sys.exit(1)

    try:
        setup_sheets(spreadsheet_id, credentials_path)
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)
    except APIError as e:
        print(f"\n✗ ERROR: Google API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
