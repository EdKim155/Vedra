#!/usr/bin/env python3
"""
Script to test Google Sheets connection and functionality.

This script verifies that Google Sheets integration is working correctly.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cars_bot.sheets import (
    AnalyticsRow,
    GoogleSheetsManager,
    LogLevel,
    LogRow,
)


def test_connection() -> None:
    """Test basic connection to Google Sheets."""
    print("=" * 60)
    print("Testing Google Sheets Connection")
    print("=" * 60)

    # Get credentials from environment
    credentials_path = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/google_service_account.json"
    )
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_ID environment variable not set!")
        print("Set it in .env file or export it:")
        print("export GOOGLE_SHEETS_ID='your_spreadsheet_id'")
        sys.exit(1)

    print(f"\nCredentials: {credentials_path}")
    print(f"Spreadsheet ID: {spreadsheet_id}")

    try:
        # Initialize manager
        print("\n1. Initializing Google Sheets Manager...")
        manager = GoogleSheetsManager(
            credentials_path=credentials_path,
            spreadsheet_id=spreadsheet_id,
            cache_ttl=60,
        )
        print("   ✓ Manager initialized successfully")

        # Test reading channels
        print("\n2. Reading channels...")
        channels = manager.get_channels(use_cache=False)
        print(f"   ✓ Found {len(channels)} channels")
        for channel in channels[:3]:  # Show first 3
            print(f"     - {channel.title} (@{channel.username})")
            print(f"       Active: {channel.is_active}, Posts: {channel.total_posts}")

        # Test reading filter settings
        print("\n3. Reading filter settings...")
        filters = manager.get_filter_settings(use_cache=False)
        print(f"   ✓ Min confidence: {filters.min_confidence_score}")
        print(f"   ✓ Global keywords: {filters.keywords_list}")
        if filters.min_price or filters.max_price:
            print(f"   ✓ Price range: {filters.min_price} - {filters.max_price}")

        # Test writing log
        print("\n4. Testing log writing...")
        log_entry = LogRow.create(
            level=LogLevel.INFO,
            message="Test log entry from test script",
            component="test_google_sheets.py",
        )
        manager.write_log(log_entry)
        print("   ✓ Log entry written successfully")

        # Test writing analytics (optional - uncomment to test)
        # print("\n5. Testing analytics writing...")
        # analytics = AnalyticsRow(
        #     date=datetime.utcnow(),
        #     posts_processed=10,
        #     posts_published=8,
        #     new_subscribers=5,
        #     active_subscriptions=100,
        #     contact_requests=25,
        #     revenue=1500.0,
        # )
        # manager.write_analytics(analytics)
        # print("   ✓ Analytics written successfully")

        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        print("\nGoogle Sheets integration is working correctly.")
        print("You can now use GoogleSheetsManager in your application.")

    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nMake sure:")
        print("1. Google Service Account JSON file exists")
        print("2. Path in GOOGLE_SERVICE_ACCOUNT_FILE is correct")
        sys.exit(1)

    except ValueError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nMake sure:")
        print("1. GOOGLE_SHEETS_ID is correct")
        print("2. Service Account has access to the spreadsheet")
        print("3. Required sheets exist in the spreadsheet")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def show_cache_demo() -> None:
    """Demonstrate caching functionality."""
    print("\n" + "=" * 60)
    print("Cache Demo")
    print("=" * 60)

    credentials_path = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/google_service_account.json"
    )
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

    manager = GoogleSheetsManager(
        credentials_path=credentials_path,
        spreadsheet_id=spreadsheet_id,
        cache_ttl=10,  # Short TTL for demo
    )

    import time

    print("\n1. First call (will fetch from Google Sheets)...")
    start = time.time()
    channels1 = manager.get_channels(use_cache=True)
    duration1 = time.time() - start
    print(f"   Took {duration1:.3f}s, found {len(channels1)} channels")

    print("\n2. Second call (will use cache)...")
    start = time.time()
    channels2 = manager.get_channels(use_cache=True)
    duration2 = time.time() - start
    print(f"   Took {duration2:.3f}s, found {len(channels2)} channels")

    print(f"\n   Cache speedup: {duration1/duration2:.1f}x faster!")

    print("\n3. Clearing cache...")
    manager.clear_cache()
    print("   Cache cleared")

    print("\n4. Third call (will fetch from Google Sheets again)...")
    start = time.time()
    channels3 = manager.get_channels(use_cache=True)
    duration3 = time.time() - start
    print(f"   Took {duration3:.3f}s, found {len(channels3)} channels")


if __name__ == "__main__":
    # Run basic tests
    test_connection()

    # Ask if user wants to see cache demo
    if len(sys.argv) > 1 and sys.argv[1] == "--cache-demo":
        show_cache_demo()
    else:
        print("\nTip: Run with --cache-demo to see caching in action")
