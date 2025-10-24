#!/usr/bin/env python3
"""
Script for creating Telegram User Session for channel monitoring.

This script should be run once to create a session file that will be used
by the monitoring service. The session file will be saved in the sessions
directory and should be kept secure.

Usage:
    python scripts/create_session.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment variables before importing settings
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from cars_bot.config.settings import TelegramSessionConfig


async def create_session():
    """
    Create Telegram user session interactively.
    
    This function guides the user through the authentication process
    and creates a session file that can be reused.
    """
    print("=" * 60)
    print("TELEGRAM USER SESSION CREATOR")
    print("=" * 60)
    print()
    
    try:
        settings = TelegramSessionConfig()
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        print()
        print("Make sure you have a .env file with required variables:")
        print("  - TELEGRAM_API_ID")
        print("  - TELEGRAM_API_HASH")
        print("  - TELEGRAM_SESSION_NAME (optional)")
        print("  - TELEGRAM_SESSION_DIR (optional)")
        return False
    
    print(f"📱 API ID: {settings.api_id}")
    print(f"🔑 API Hash: {settings.api_hash.get_secret_value()[:8]}...")
    print(f"📁 Session file: {settings.session_path}")
    print()
    
    # Check if session already exists
    if settings.session_path.exists():
        print(f"⚠️  Session file already exists: {settings.session_path}")
        overwrite = input("Do you want to overwrite it? (yes/no): ").strip().lower()
        if overwrite not in ["yes", "y"]:
            print("❌ Session creation cancelled.")
            return False
        print()
    
    # Create session directory
    settings.session_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize Telethon client
    client = TelegramClient(
        str(settings.session_path),
        settings.api_id,
        settings.api_hash.get_secret_value(),
        sequential_updates=True,
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("📞 Phone number is required for authorization.")
            print("Format: +1234567890 (international format with +)")
            print()
            
            # Get phone number
            phone = input("Enter your phone number: ").strip()
            
            if not phone:
                print("❌ Phone number is required.")
                return False
            
            try:
                # Send code request
                print()
                print(f"📨 Sending code to {phone}...")
                await client.send_code_request(phone)
                
                # Get code from user
                print()
                print("📬 Check your Telegram app for the authorization code.")
                code = input("Enter the code you received: ").strip()
                
                if not code:
                    print("❌ Code is required.")
                    return False
                
                try:
                    # Try to sign in
                    print()
                    print("🔐 Signing in...")
                    await client.sign_in(phone, code)
                    
                except SessionPasswordNeededError:
                    # 2FA is enabled
                    print()
                    print("🔒 Two-Factor Authentication is enabled on this account.")
                    password = input("Enter your 2FA password: ").strip()
                    
                    if not password:
                        print("❌ Password is required.")
                        return False
                    
                    await client.sign_in(password=password)
                
                print()
                print("✅ Successfully authenticated!")
                
            except PhoneNumberInvalidError:
                print(f"❌ Invalid phone number: {phone}")
                print("Make sure to use international format with + prefix.")
                return False
            
            except PhoneCodeInvalidError:
                print("❌ Invalid authorization code.")
                return False
            
            except ApiIdInvalidError:
                print("❌ Invalid API ID or API Hash.")
                print("Get your credentials from https://my.telegram.org/apps")
                return False
        
        else:
            print("✅ Already authorized!")
        
        # Get user information
        me = await client.get_me()
        print()
        print("=" * 60)
        print("SESSION CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"👤 User: {me.first_name} {me.last_name or ''}")
        print(f"📱 Username: @{me.username if me.username else 'N/A'}")
        print(f"🆔 User ID: {me.id}")
        print(f"📞 Phone: {me.phone}")
        print()
        print(f"💾 Session saved to: {settings.session_path}")
        print()
        
        # Save as string session (backup)
        string_session = StringSession.save(client.session)
        backup_path = settings.session_path.parent / f"{settings.session_name}_backup.txt"
        
        with open(backup_path, "w") as f:
            f.write(string_session)
        
        print(f"💾 Backup string session saved to: {backup_path}")
        print()
        
        # Important notes
        print("⚠️  IMPORTANT SECURITY NOTES:")
        print("=" * 60)
        print("1. Keep the session file secure - it grants full access to your account")
        print("2. Never commit session files to Git (add to .gitignore)")
        print("3. Create regular backups of the session file")
        print("4. Use a dedicated account for monitoring (not your personal account)")
        print("5. Subscribe this account to all channels you want to monitor")
        print()
        
        # Recommendations
        print("📋 NEXT STEPS:")
        print("=" * 60)
        print("1. Subscribe this account to all channels you want to monitor")
        print("2. Add channels to Google Sheets 'Каналы для мониторинга'")
        print("3. Start the monitoring service")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await client.disconnect()
        print("👋 Disconnected from Telegram.")


async def test_session():
    """
    Test existing session to verify it works.
    """
    print("=" * 60)
    print("TESTING EXISTING SESSION")
    print("=" * 60)
    print()
    
    try:
        settings = TelegramSessionConfig()
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return False
    
    if not settings.session_path.exists():
        print(f"❌ Session file not found: {settings.session_path}")
        print("Run this script without arguments to create a new session.")
        return False
    
    print(f"📁 Testing session: {settings.session_path}")
    print()
    
    client = TelegramClient(
        str(settings.session_path),
        settings.api_id,
        settings.api_hash.get_secret_value(),
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Session is not authorized. Please create a new session.")
            return False
        
        me = await client.get_me()
        print("✅ Session is valid!")
        print()
        print(f"👤 User: {me.first_name} {me.last_name or ''}")
        print(f"📱 Username: @{me.username if me.username else 'N/A'}")
        print(f"🆔 User ID: {me.id}")
        print()
        
        # Get dialogs count
        dialogs = await client.get_dialogs(limit=None)
        print(f"💬 Available dialogs: {len(dialogs)}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing session: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await client.disconnect()


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test existing session
        success = asyncio.run(test_session())
    else:
        # Create new session
        success = asyncio.run(create_session())
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


