#!/usr/bin/env python3
"""
Script to automatically create a Google Sheets template with proper structure.

This script creates a new Google Spreadsheet with all required sheets
and proper formatting for the CARS BOT project.

Usage:
    python scripts/create_sheets_template.py

    Optional arguments:
    --title TITLE           Custom title for the spreadsheet (default: "CARS BOT - Configuration")
    --share EMAIL           Email address to share the spreadsheet with (can be used multiple times)
    --credentials PATH      Path to Google Service Account JSON file
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


# Define sheet structures
SHEET_STRUCTURES = {
    "Каналы для мониторинга": {
        "headers": [
            "ID",
            "Username канала",
            "Название канала",
            "Активен",
            "Ключевые слова",
            "Дата добавления",
            "Всего постов",
            "Опубликовано",
            "Последний пост",
        ],
        "validations": {
            "D": {"type": "BOOLEAN"},  # Активен
        },
        "examples": {
            1: ["1", "@avito_auto", "Авито Авто", "TRUE", "продам,авто", "2025-10-23", "0", "0", ""],
            2: ["2", "@auto_ru", "Авто.ру", "TRUE", "автомобиль,машина", "2025-10-23", "0", "0", ""],
        },
        "comments": {
            "B1": "Формат: @username или t.me/channelname",
            "E1": "Ключевые слова через запятую (опционально)",
            "D1": "TRUE для включения мониторинга, FALSE для отключения",
        },
    },
    "Настройки фильтров": {
        "headers": [
            "Параметр",
            "Значение",
        ],
        "examples": {
            1: ["Глобальные ключевые слова", "продам,авто,машина,автомобиль"],
            2: ["Порог уверенности AI", "0.75"],
            3: ["Минимальная цена", "100000"],
            4: ["Максимальная цена", "5000000"],
            5: ["Исключаемые слова", "аварийный,битый,утиль"],
        },
        "comments": {
            "A1": "Название параметра",
            "B1": "Значение параметра",
            "B2": "Порог от 0.0 до 1.0 (чем выше, тем строже фильтр)",
        },
    },
    "Подписчики": {
        "headers": [
            "User ID",
            "Username",
            "Имя",
            "Тип подписки",
            "Активна",
            "Дата начала",
            "Дата окончания",
            "Дата регистрации",
            "Запросов контактов",
        ],
        "validations": {
            "D": {"type": "ONE_OF_LIST", "values": ["FREE", "MONTHLY", "YEARLY"]},
            "E": {"type": "BOOLEAN"},
        },
        "examples": {
            1: ["123456789", "@username", "Иван Иванов", "FREE", "TRUE", "2025-10-23", "", "2025-10-23", "0"],
            2: ["987654321", "@user2", "Петр Петров", "MONTHLY", "TRUE", "2025-10-23", "2025-11-23", "2025-10-20", "5"],
        },
        "comments": {
            "A1": "Telegram User ID пользователя",
            "D1": "FREE, MONTHLY или YEARLY",
            "E1": "TRUE если подписка активна",
        },
    },
    "Аналитика": {
        "headers": [
            "Дата",
            "Обработано постов",
            "Опубликовано",
            "Новых подписчиков",
            "Активных подписок",
            "Запросов контактов",
            "Доход",
        ],
        "examples": {
            1: ["2025-10-23", "50", "45", "10", "100", "120", "15000"],
            2: ["2025-10-22", "48", "42", "8", "90", "110", "12000"],
        },
        "comments": {
            "A1": "Дата статистики",
            "G1": "Доход в рублях за день",
        },
    },
    "Очередь публикаций": {
        "headers": [
            "ID поста",
            "Канал-источник",
            "Дата обработки",
            "Марка/Модель",
            "Цена",
            "Статус",
            "Ссылка на оригинал",
            "Примечание",
        ],
        "validations": {
            "F": {"type": "ONE_OF_LIST", "values": ["PENDING", "APPROVED", "REJECTED", "PUBLISHED"]},
        },
        "examples": {
            1: ["1", "@avito_auto", "2025-10-23 14:30", "Toyota Camry", "1500000", "PENDING", "https://t.me/...", ""],
            2: ["2", "@auto_ru", "2025-10-23 15:00", "BMW X5", "2500000", "APPROVED", "https://t.me/...", "Отличное объявление"],
        },
        "comments": {
            "F1": "PENDING/APPROVED/REJECTED/PUBLISHED",
            "H1": "Используйте для заметок по модерации",
        },
    },
    "Логи": {
        "headers": [
            "Дата/время",
            "Тип события",
            "Описание",
            "Компонент",
        ],
        "validations": {
            "B": {"type": "ONE_OF_LIST", "values": ["ERROR", "WARNING", "INFO"]},
        },
        "examples": {
            1: ["2025-10-23 14:30:00", "INFO", "Система запущена", "main"],
            2: ["2025-10-23 14:35:00", "WARNING", "Превышен лимит API", "google_sheets"],
        },
        "comments": {
            "B1": "ERROR для ошибок, WARNING для предупреждений, INFO для информации",
        },
    },
}


def create_spreadsheet(
    credentials_path: str | Path,
    title: str = "CARS BOT - Configuration",
) -> gspread.Spreadsheet:
    """
    Create a new Google Spreadsheet with all required sheets.

    Args:
        credentials_path: Path to Google Service Account JSON credentials
        title: Title for the new spreadsheet

    Returns:
        Created spreadsheet object

    Raises:
        FileNotFoundError: If credentials file not found
        APIError: If Google API request fails
    """
    # Authenticate
    print(f"Authenticating with credentials from: {credentials_path}")
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

    # Create spreadsheet
    print(f"\nCreating spreadsheet: {title}")
    spreadsheet = client.create(title)
    print(f"✓ Spreadsheet created with ID: {spreadsheet.id}")
    print(f"  URL: {spreadsheet.url}")

    return spreadsheet


def format_header_row(worksheet: gspread.Worksheet) -> None:
    """
    Format the header row with bold text and background color.

    Args:
        worksheet: Worksheet to format
    """
    # Format header row (row 1)
    worksheet.format("1:1", {
        "backgroundColor": {
            "red": 0.2,
            "green": 0.6,
            "blue": 0.86,
        },
        "textFormat": {
            "bold": True,
            "foregroundColor": {
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
            },
        },
        "horizontalAlignment": "CENTER",
    })

    # Freeze header row
    worksheet.freeze(rows=1)


def add_data_validation(
    worksheet: gspread.Worksheet,
    validations: dict[str, dict[str, Any]],
) -> None:
    """
    Add data validation rules to columns.

    Args:
        worksheet: Worksheet to add validation to
        validations: Dict mapping column letters to validation rules
    """
    for col_letter, validation_config in validations.items():
        validation_type = validation_config["type"]

        if validation_type == "BOOLEAN":
            # Boolean validation (TRUE/FALSE dropdown)
            rule = gspread.data_validation.DataValidationRule(
                gspread.data_validation.BooleanCondition("ONE_OF_LIST", ["TRUE", "FALSE"]),
                showCustomUi=True,
            )
        elif validation_type == "ONE_OF_LIST":
            # List validation with custom values
            rule = gspread.data_validation.DataValidationRule(
                gspread.data_validation.BooleanCondition("ONE_OF_LIST", validation_config["values"]),
                showCustomUi=True,
            )
        else:
            continue

        # Apply validation to entire column (starting from row 2)
        range_name = f"{col_letter}2:{col_letter}1000"
        rules = gspread.data_validation.get_data_validation_rules(worksheet)
        rules.append(gspread.data_validation.DataValidationRule(
            rule.condition,
            showCustomUi=True,
        ))

        worksheet.add_validation(range_name, rule)


def add_comments(
    worksheet: gspread.Worksheet,
    comments: dict[str, str],
) -> None:
    """
    Add comments to cells.

    Args:
        worksheet: Worksheet to add comments to
        comments: Dict mapping cell addresses (e.g., "A1") to comment text
    """
    for cell_address, comment_text in comments.items():
        # Note: gspread doesn't have a direct method to add notes/comments
        # This would require using the Google Sheets API directly
        # For now, we'll skip this or add it as a separate feature
        pass


def create_sheet(
    spreadsheet: gspread.Spreadsheet,
    sheet_name: str,
    structure: dict[str, Any],
) -> None:
    """
    Create and configure a single sheet.

    Args:
        spreadsheet: Parent spreadsheet
        sheet_name: Name of the sheet to create
        structure: Sheet structure configuration
    """
    print(f"\n  Creating sheet: {sheet_name}")

    # Create worksheet
    try:
        worksheet = spreadsheet.add_worksheet(
            title=sheet_name,
            rows=1000,
            cols=len(structure["headers"]),
        )
    except APIError as e:
        if "already exists" in str(e):
            print(f"    Sheet already exists, using existing sheet")
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            raise

    # Add headers
    print(f"    Adding headers...")
    worksheet.update("A1", [structure["headers"]])

    # Format header row
    print(f"    Formatting headers...")
    format_header_row(worksheet)

    # Add data validation
    if "validations" in structure:
        print(f"    Adding data validation...")
        add_data_validation(worksheet, structure["validations"])

    # Add example data
    if "examples" in structure:
        print(f"    Adding example data...")
        for row_num, row_data in structure["examples"].items():
            cell_range = f"A{row_num + 1}"
            worksheet.update(cell_range, [row_data])

    # Resize columns to fit content
    print(f"    Adjusting column widths...")
    for i in range(len(structure["headers"])):
        col_letter = chr(65 + i)  # A, B, C, ...
        worksheet.columns_auto_resize(i, i)

    print(f"    ✓ Sheet '{sheet_name}' created successfully")


def main() -> None:
    """Main function to create Google Sheets template."""
    parser = argparse.ArgumentParser(
        description="Create Google Sheets template for CARS BOT",
    )
    parser.add_argument(
        "--title",
        default="CARS BOT - Configuration",
        help="Title for the spreadsheet",
    )
    parser.add_argument(
        "--share",
        action="append",
        dest="share_emails",
        help="Email addresses to share the spreadsheet with (can be used multiple times)",
    )
    parser.add_argument(
        "--credentials",
        default="./secrets/google_service_account.json",
        help="Path to Google Service Account JSON credentials",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Creating Google Sheets Template for CARS BOT")
    print("=" * 70)

    try:
        # Create spreadsheet
        spreadsheet = create_spreadsheet(
            credentials_path=args.credentials,
            title=args.title,
        )

        # Remove default "Sheet1"
        try:
            default_sheet = spreadsheet.sheet1
            spreadsheet.del_worksheet(default_sheet)
            print("  ✓ Removed default sheet")
        except Exception:
            pass

        # Create all required sheets
        print("\nCreating sheets:")
        for sheet_name, structure in SHEET_STRUCTURES.items():
            create_sheet(spreadsheet, sheet_name, structure)

        # Share with specified emails
        if args.share_emails:
            print("\nSharing spreadsheet:")
            for email in args.share_emails:
                print(f"  Sharing with: {email}")
                spreadsheet.share(
                    email,
                    perm_type="user",
                    role="writer",
                    notify=True,
                    email_message=f"Google Sheets template for CARS BOT project: {args.title}",
                )
                print(f"    ✓ Shared with {email}")

        # Print final information
        print("\n" + "=" * 70)
        print("✓ Google Sheets template created successfully!")
        print("=" * 70)
        print(f"\nSpreadsheet ID: {spreadsheet.id}")
        print(f"Spreadsheet URL: {spreadsheet.url}")
        print("\nNext steps:")
        print("1. Add this spreadsheet ID to your .env file:")
        print(f"   GOOGLE_SHEETS_ID={spreadsheet.id}")
        print("2. Share the spreadsheet with your service account email")
        print("3. Start adding your channel configurations")
        print("\nSheets created:")
        for sheet_name in SHEET_STRUCTURES.keys():
            print(f"  ✓ {sheet_name}")

    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nMake sure:")
        print("1. Google Service Account JSON file exists")
        print("2. Path to credentials is correct")
        print(f"   Current path: {args.credentials}")
        sys.exit(1)

    except APIError as e:
        print(f"\n✗ ERROR: Google API error: {e}")
        print("\nMake sure:")
        print("1. Google Sheets API is enabled in your project")
        print("2. Google Drive API is enabled in your project")
        print("3. Service Account has necessary permissions")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
