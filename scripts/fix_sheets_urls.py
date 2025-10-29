#!/usr/bin/env python3
"""
Fix URLs in Google Sheets - replace with usernames.
"""

import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.config import get_settings


def main():
    print("=" * 80)
    print("🔧 ИСПРАВЛЕНИЕ URL В GOOGLE SHEETS")
    print("=" * 80)
    print()
    
    settings = get_settings()
    manager = GoogleSheetsManager(
        credentials_path=settings.google.credentials_file,
        spreadsheet_id=settings.google.spreadsheet_id
    )
    
    # Get raw worksheet
    worksheet = manager._get_worksheet(manager.SHEET_CHANNELS)
    
    # Get all values
    all_values = worksheet.get_all_values()
    
    if not all_values:
        print("❌ Таблица пустая!")
        return 1
    
    header = all_values[0]
    data_rows = all_values[1:]
    
    fixed_rows = []
    
    for row_num, row in enumerate(data_rows, 2):  # Start from row 2
        if len(row) < 2:
            continue
        
        username_cell = row[1]  # Column B (index 1)
        
        # Check if it's a URL
        if 'https://t.me/' in username_cell:
            # Extract username
            match = re.search(r'https://t\.me/([^/]+)', username_cell)
            
            if match:
                old_value = username_cell
                new_value = match.group(1)  # Without @
                
                print(f"Строка {row_num}: {old_value} → {new_value}")
                
                fixed_rows.append({
                    'row': row_num,
                    'col': 2,  # Column B
                    'value': new_value
                })
    
    if fixed_rows:
        print()
        print(f"📝 Обновляю {len(fixed_rows)} строк...")
        
        # Prepare batch update
        import gspread
        updates = []
        for fix in fixed_rows:
            updates.append(gspread.Cell(fix['row'], fix['col'], fix['value']))
        
        manager.rate_limiter.wait_if_needed()
        worksheet.update_cells(updates)
        
        print(f"✅ Обновлено!")
    else:
        print("✅ Все URL уже исправлены")
    
    print()
    print("=" * 80)
    print(f"✅ Готово!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())




