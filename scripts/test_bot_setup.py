#!/usr/bin/env python3
"""
Script to test bot setup and configuration.

Checks that all required modules and dependencies are properly configured.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from cars_bot.config import get_settings
        print("✅ Config module OK")
    except ImportError as e:
        print(f"❌ Config module failed: {e}")
        return False
    
    try:
        from cars_bot.database.session import init_database
        print("✅ Database module OK")
    except ImportError as e:
        print(f"❌ Database module failed: {e}")
        return False
    
    try:
        from cars_bot.bot import CarsBot
        print("✅ Bot module OK")
    except ImportError as e:
        print(f"❌ Bot module failed: {e}")
        return False
    
    try:
        from cars_bot.bot.handlers import (
            start_handler,
            subscription_handler,
            contacts_handler,
            admin_handler,
        )
        print("✅ All handlers OK")
    except ImportError as e:
        print(f"❌ Handlers failed: {e}")
        return False
    
    try:
        from cars_bot.bot.middlewares import (
            UserRegistrationMiddleware,
            SubscriptionCheckMiddleware,
            LoggingMiddleware,
        )
        print("✅ All middlewares OK")
    except ImportError as e:
        print(f"❌ Middlewares failed: {e}")
        return False
    
    try:
        from cars_bot.bot.keyboards import inline_keyboards, reply_keyboards
        print("✅ All keyboards OK")
    except ImportError as e:
        print(f"❌ Keyboards failed: {e}")
        return False
    
    return True


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from cars_bot.config import get_settings
        settings = get_settings()
        
        print(f"✅ App name: {settings.app_name}")
        print(f"✅ Debug mode: {settings.debug}")
        print(f"✅ Database URL: {settings.database_url[:30]}...")
        print(f"✅ Bot token configured: {'Yes' if settings.bot_token else 'No'}")
        print(f"✅ OpenAI API key configured: {'Yes' if settings.openai_api_key else 'No'}")
        
        return True
    
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False


def test_database_models():
    """Test database models."""
    print("\nTesting database models...")
    
    try:
        from cars_bot.database.models import (
            User,
            Subscription,
            Post,
            Channel,
            CarData,
            SellerContact,
            ContactRequest,
        )
        print("✅ All database models OK")
        return True
    
    except ImportError as e:
        print(f"❌ Database models failed: {e}")
        return False


def test_aiogram_version():
    """Test aiogram version."""
    print("\nTesting aiogram version...")
    
    try:
        import aiogram
        version = aiogram.__version__
        
        # Check if version is 3.x
        major_version = int(version.split('.')[0])
        
        if major_version >= 3:
            print(f"✅ aiogram version: {version} (OK)")
            return True
        else:
            print(f"❌ aiogram version: {version} (need 3.x)")
            return False
    
    except Exception as e:
        print(f"❌ aiogram check failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Cars Bot - Setup Test")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_configuration()))
    results.append(("Database Models", test_database_models()))
    results.append(("aiogram Version", test_aiogram_version()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! Bot is ready to run.")
        print("\nNext steps:")
        print("1. Make sure .env file is properly configured")
        print("2. Run migrations: make migrate")
        print("3. Start the bot: make run-bot")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())



