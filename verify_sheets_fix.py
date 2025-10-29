#!/usr/bin/env python3
"""
Simple verification script that checks source code without importing.
"""

import os
import re

def check_file_content(filepath, patterns, name):
    """Check if file contains expected patterns."""
    print(f"\n[{name}] Checking {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    all_passed = True
    for pattern_name, pattern, should_exist in patterns:
        found = bool(re.search(pattern, content, re.MULTILINE | re.DOTALL))
        
        if should_exist and found:
            print(f"✅ {pattern_name}")
        elif not should_exist and not found:
            print(f"✅ {pattern_name}")
        elif should_exist and not found:
            print(f"❌ Missing: {pattern_name}")
            all_passed = False
        else:  # not should_exist and found
            print(f"❌ Should not exist: {pattern_name}")
            all_passed = False
    
    return all_passed

print("=" * 60)
print("Verifying Sheets Fix Implementation")
print("=" * 60)

all_checks_passed = True

# Check 1: sheets_tasks.py
patterns = [
    ("add_new_user_to_sheets_task function", r'def add_new_user_to_sheets_task\(', True),
    ("add_new_user_to_sheets_task decorator", r'name="cars_bot\.tasks\.sheets_tasks\.add_new_user_to_sheets_task"', True),
    ("sync_subscribers_task uses safe mode", r'update_subscriber_safe_fields', True),
    ("sync_subscribers_task gets existing subscribers", r'get_subscribers\(use_cache=False\)', True),
    ("sync_subscribers_task adds new users", r'add_subscriber\(subscriber_row\)', True),
    ("sync_subscriptions_from_sheets_task has ONE-WAY comment", r'ONE-WAY sync', True),
    ("sync_subscriptions_from_sheets_task removed write-back", r'REMOVED: Do NOT write back', True),
    ("deprecated update_subscribers NOT used in sync_subscribers_task", r'def sync_subscribers_task.*?update_subscribers\(subscribers_data\)', False),
]

if not check_file_content('src/cars_bot/tasks/sheets_tasks.py', patterns, '1'):
    all_checks_passed = False

# Check 2: __init__.py exports
patterns = [
    ("add_new_user_to_sheets_task import", r'from cars_bot\.tasks\.sheets_tasks import \(.*?add_new_user_to_sheets_task', True),
    ("sync_subscriptions_from_sheets_task import", r'from cars_bot\.tasks\.sheets_tasks import \(.*?sync_subscriptions_from_sheets_task', True),
    ("add_new_user_to_sheets_task in __all__", r'__all__.*?"add_new_user_to_sheets_task"', True),
    ("sync_subscriptions_from_sheets_task in __all__", r'__all__.*?"sync_subscriptions_from_sheets_task"', True),
]

if not check_file_content('src/cars_bot/tasks/__init__.py', patterns, '2'):
    all_checks_passed = False

# Check 3: user_registration.py middleware
patterns = [
    ("_add_user_to_sheets_async function", r'def _add_user_to_sheets_async\(', True),
    ("add_new_user_to_sheets_task import", r'from cars_bot\.tasks\.sheets_tasks import add_new_user_to_sheets_task', True),
    ("add_new_user_to_sheets_task.apply_async call", r'add_new_user_to_sheets_task\.apply_async', True),
]

if not check_file_content('src/cars_bot/bot/middlewares/user_registration.py', patterns, '3'):
    all_checks_passed = False

# Check 4: sheets/manager.py
patterns = [
    ("update_subscriber_safe_fields method", r'def update_subscriber_safe_fields\(', True),
    ("update_subscribers deprecated warning", r'DEPRECATED.*overwrites manual changes', True),
    ("add_subscriber method", r'def add_subscriber\(', True),
]

if not check_file_content('src/cars_bot/sheets/manager.py', patterns, '4'):
    all_checks_passed = False

print("\n" + "=" * 60)
if all_checks_passed:
    print("✅ All verification checks passed!")
    print("=" * 60)
    print("\nImplementation summary:")
    print("1. ✅ add_new_user_to_sheets_task created and configured")
    print("2. ✅ sync_subscribers_task uses safe mode (no overwrite)")
    print("3. ✅ sync_subscriptions_from_sheets_task removed write-back")
    print("4. ✅ Tasks properly exported in __init__.py")
    print("5. ✅ Middleware calls new task for user registration")
    print("\nExpected behavior:")
    print("- New users automatically added to Sheets on registration")
    print("- Manual subscription changes in Sheets NOT overwritten")
    print("- Google Sheets is source of truth for subscription management")
else:
    print("❌ Some checks failed!")
    print("=" * 60)
    exit(1)
