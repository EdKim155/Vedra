#!/usr/bin/env python3
"""
Diagnostic script to check Google Sheets structure.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.config import get_settings


def main():
    print("=" * 80)
    print("📊 GOOGLE SHEETS STRUCTURE CHECK")
    print("=" * 80)
    print()
    
    try:
        settings = get_settings()
        manager = GoogleSheetsManager(
            credentials_path=settings.google.credentials_file,
            spreadsheet_id=settings.google.spreadsheet_id
        )
        
        # Get raw worksheet
        worksheet = manager._get_worksheet(manager.SHEET_CHANNELS)
        
        # Get all values (including header)
        all_values = worksheet.get_all_values()
        
        if not all_values:
            print("❌ Таблица пустая!")
            return
        
        # Show header
        print("📋 ЗАГОЛОВКИ (строка 1):")
        print("-" * 80)
        header = all_values[0]
        for i, col in enumerate(header, 1):
            print(f"  Столбец {chr(64+i)}: '{col}'")
        print()
        
        # Show first 10 data rows
        print("📝 ПЕРВЫЕ 10 СТРОК ДАННЫХ:")
        print("-" * 80)
        
        data_rows = all_values[1:11]  # Skip header, take next 10
        
        for row_num, row in enumerate(data_rows, 2):  # Start from row 2
            print(f"\nСтрока {row_num}:")
            
            # Pad row to match header length
            while len(row) < len(header):
                row.append('')
            
            for i, (col_name, value) in enumerate(zip(header, row), 1):
                if value:  # Only show non-empty
                    print(f"  {chr(64+i)} ({col_name}): '{value}'")
                else:
                    print(f"  {chr(64+i)} ({col_name}): <пусто>")
        
        print()
        print("=" * 80)
        print(f"✅ Всего строк в таблице: {len(all_values)}")
        print(f"✅ Строк данных (без заголовка): {len(all_values) - 1}")
        print()
        
        # Try to parse with ChannelRow model
        print("🔍 ПАРСИНГ ЧЕРЕЗ ChannelRow:")
        print("-" * 80)
        
        channels = manager.get_channels()
        print(f"✅ Успешно прочитано каналов: {len(channels)}")
        print()
        
        for i, ch in enumerate(channels, 1):
            print(f"{i}. {ch.username}")
            print(f"   Title: {ch.title}")
            print(f"   Active: {ch.is_active}")
            print(f"   Date added: {ch.date_added}")
            print(f"   Published: {ch.published_posts}")
            print(f"   Last post: {ch.last_post_link or '<пусто>'}")
            print()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())




