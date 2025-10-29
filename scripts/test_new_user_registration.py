#!/usr/bin/env python3
"""
Test script for new user registration and Google Sheets sync.

Tests:
1. New user is automatically added to Google Sheets
2. Manual subscription changes in Google Sheets are synced to database
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from cars_bot.config import get_settings
from cars_bot.database.session import get_db_manager
from cars_bot.database.models.user import User
from cars_bot.database.models.subscription import Subscription
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.tasks.sheets_tasks import add_new_user_to_sheets_task, sync_subscriptions_from_sheets_task


async def test_new_user_registration():
    """Test that new users are automatically added to Google Sheets."""
    print("\n" + "="*60)
    print("TEST 1: New User Registration → Google Sheets")
    print("="*60)
    
    # Create test user
    test_telegram_id = 999888777  # Use unique ID for testing
    
    db_manager = get_db_manager()
    async with db_manager.session() as session:
        # Check if test user already exists
        result = await session.execute(
            select(User).where(User.telegram_user_id == test_telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✓ Test user {test_telegram_id} already exists in database")
            user = existing_user
        else:
            # Create new test user
            user = User(
                telegram_user_id=test_telegram_id,
                username="test_user_new",
                first_name="Тестовый",
                last_name="Пользователь",
                is_admin=False,
                is_blocked=False,
                contact_requests_count=0,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✓ Created new test user: {test_telegram_id}")
        
        # Trigger Google Sheets sync task (synchronously for testing)
        print(f"\n→ Adding user to Google Sheets...")
        result = add_new_user_to_sheets_task(user.id, user.telegram_user_id)
        
        if result.get("success"):
            if result.get("already_exists"):
                print(f"✓ User already exists in Google Sheets")
            else:
                print(f"✓ Successfully added user to Google Sheets")
        else:
            print(f"✗ Failed to add user to Google Sheets: {result.get('error')}")
            return False
    
    # Verify in Google Sheets
    print(f"\n→ Verifying in Google Sheets...")
    settings = get_settings()
    sheets_manager = GoogleSheetsManager(
        credentials_path=settings.google.credentials_file,
        spreadsheet_id=settings.google.spreadsheet_id
    )
    
    try:
        worksheet = sheets_manager._get_worksheet(sheets_manager.SHEET_SUBSCRIBERS)
        cell = worksheet.find(str(test_telegram_id))
        
        if cell:
            # Get row data
            row_values = worksheet.row_values(cell.row)
            print(f"\n✅ User found in Google Sheets:")
            print(f"   User ID: {row_values[0]}")
            print(f"   Username: {row_values[1]}")
            print(f"   Name: {row_values[2]}")
            print(f"   Subscription Type: {row_values[3]}")
            print(f"   Active: {row_values[4]}")
            
            # Check that it's FREE and active
            if row_values[3] == "FREE" and row_values[4] == "TRUE":
                print(f"\n✅ TEST 1 PASSED: User has FREE subscription and is ACTIVE")
                return True
            else:
                print(f"\n✗ TEST 1 FAILED: Expected FREE/TRUE, got {row_values[3]}/{row_values[4]}")
                return False
        else:
            print(f"\n✗ TEST 1 FAILED: User not found in Google Sheets")
            return False
            
    except Exception as e:
        print(f"\n✗ Error checking Google Sheets: {e}")
        return False


async def test_manual_subscription_management():
    """Test that manual subscription changes in Google Sheets are synced to database."""
    print("\n" + "="*60)
    print("TEST 2: Manual Subscription Management (Google Sheets → DB)")
    print("="*60)
    
    test_telegram_id = 999888777
    
    print(f"\n📋 INSTRUCTIONS:")
    print(f"1. Open Google Sheets 'Подписчики' tab")
    print(f"2. Find user {test_telegram_id}")
    print(f"3. Change 'Тип подписки' from FREE to MONTHLY")
    print(f"4. Ensure 'Активна' is TRUE")
    print(f"5. Save and wait a moment...")
    
    input(f"\n→ Press ENTER when ready to test sync...")
    
    # Trigger sync from Google Sheets
    print(f"\n→ Running sync_subscriptions_from_sheets_task...")
    result = sync_subscriptions_from_sheets_task()
    
    if result.get("success"):
        print(f"✓ Sync completed: {result.get('updated')} updated, {result.get('created')} created")
    else:
        print(f"✗ Sync failed")
        return False
    
    # Check database
    print(f"\n→ Checking database for subscription changes...")
    db_manager = get_db_manager()
    async with db_manager.session() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == test_telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"✗ User not found in database")
            return False
        
        # Get active subscription
        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True
            )
        )
        subscription = sub_result.scalar_one_or_none()
        
        if not subscription:
            print(f"✗ No active subscription found in database")
            return False
        
        print(f"\n✅ Subscription found in database:")
        print(f"   Type: {subscription.subscription_type.value}")
        print(f"   Active: {subscription.is_active}")
        print(f"   Start Date: {subscription.start_date}")
        print(f"   End Date: {subscription.end_date}")
        
        # Check if dates were auto-calculated
        if subscription.start_date and subscription.end_date:
            days_diff = (subscription.end_date - subscription.start_date).days
            print(f"   Duration: {days_diff} days")
            
            if subscription.subscription_type.value == "MONTHLY" and 28 <= days_diff <= 31:
                print(f"\n✅ TEST 2 PASSED: MONTHLY subscription with correct dates")
                return True
            elif subscription.subscription_type.value == "FREE":
                print(f"\n⚠️  Still FREE - please change to MONTHLY in Google Sheets and try again")
                return False
            else:
                print(f"\n✅ TEST 2 PASSED: Subscription synced from Google Sheets")
                return True
        else:
            print(f"\n✗ TEST 2 FAILED: Dates not auto-calculated")
            return False


async def test_reverse_sync():
    """Test that database changes are synced back to Google Sheets."""
    print("\n" + "="*60)
    print("TEST 3: Reverse Sync (DB → Google Sheets)")
    print("="*60)
    
    test_telegram_id = 999888777
    
    # Update contact requests count in database
    print(f"\n→ Updating contact requests count in database...")
    db_manager = get_db_manager()
    async with db_manager.session() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == test_telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"✗ User not found")
            return False
        
        old_count = user.contact_requests_count
        user.contact_requests_count += 1
        await session.commit()
        new_count = user.contact_requests_count
        
        print(f"✓ Updated contact requests: {old_count} → {new_count}")
    
    # Sync to Google Sheets
    from cars_bot.tasks.sheets_tasks import sync_subscribers_task
    print(f"\n→ Running sync_subscribers_task (DB → Sheets)...")
    result = sync_subscribers_task()
    
    if result.get("success"):
        print(f"✓ Sync completed: {result.get('subscribers_count')} subscribers synced")
    else:
        print(f"✗ Sync failed")
        return False
    
    # Verify in Google Sheets
    print(f"\n→ Verifying in Google Sheets...")
    settings = get_settings()
    sheets_manager = GoogleSheetsManager(
        credentials_path=settings.google.credentials_file,
        spreadsheet_id=settings.google.spreadsheet_id
    )
    
    try:
        worksheet = sheets_manager._get_worksheet(sheets_manager.SHEET_SUBSCRIBERS)
        cell = worksheet.find(str(test_telegram_id))
        
        if cell:
            row_values = worksheet.row_values(cell.row)
            sheets_count = int(row_values[8]) if len(row_values) > 8 and row_values[8] else 0
            
            print(f"\n✓ Contact requests in Google Sheets: {sheets_count}")
            
            if sheets_count == new_count:
                print(f"\n✅ TEST 3 PASSED: Database changes synced to Google Sheets")
                return True
            else:
                print(f"\n✗ TEST 3 FAILED: Expected {new_count}, got {sheets_count}")
                return False
        else:
            print(f"\n✗ User not found in Google Sheets")
            return False
            
    except Exception as e:
        print(f"\n✗ Error checking Google Sheets: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n🧪 TESTING NEW USER REGISTRATION & MANUAL SUBSCRIPTION MANAGEMENT")
    print("="*60)
    
    results = []
    
    # Test 1: New user registration
    try:
        result1 = await test_new_user_registration()
        results.append(("New User Registration", result1))
    except Exception as e:
        print(f"\n✗ Test 1 failed with error: {e}")
        results.append(("New User Registration", False))
    
    # Test 2: Manual subscription management
    try:
        result2 = await test_manual_subscription_management()
        results.append(("Manual Subscription Management", result2))
    except Exception as e:
        print(f"\n✗ Test 2 failed with error: {e}")
        results.append(("Manual Subscription Management", False))
    
    # Test 3: Reverse sync
    try:
        result3 = await test_reverse_sync()
        results.append(("Reverse Sync", result3))
    except Exception as e:
        print(f"\n✗ Test 3 failed with error: {e}")
        results.append(("Reverse Sync", False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED")
    
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

