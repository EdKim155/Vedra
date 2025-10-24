#!/usr/bin/env python3
"""
Script to manually subscribe to all channels from database.

This script will:
1. Load all active channels from database
2. Subscribe to each channel (if public)
3. Report subscription status

Usage:
    python scripts/subscribe_to_channels.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger
from sqlalchemy import select
from telethon import TelegramClient
from telethon.errors import ChannelPrivateError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel

from cars_bot.config import get_settings
from cars_bot.database.models.channel import Channel as DBChannel
from cars_bot.database.session import get_db_manager, init_database


async def subscribe_to_all_channels():
    """Subscribe to all channels from database."""
    
    print("=" * 60)
    print("TELEGRAM CHANNEL AUTO-SUBSCRIPTION")
    print("=" * 60)
    print()
    
    # Initialize settings
    settings = get_settings()
    
    # Initialize database
    init_database(str(settings.database.url), echo=False)
    
    # Initialize Telegram client
    client = TelegramClient(
        str(settings.telegram.session_path),
        settings.telegram.api_id,
        settings.telegram.api_hash.get_secret_value(),
    )
    
    try:
        # Connect
        await client.connect()
        
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Session is not authorized. Please run scripts/create_session.py"
            )
        
        # Get current user
        me = await client.get_me()
        print(f"✅ Connected as: {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username if me.username else 'N/A'}")
        print()
        
        # Load channels from database
        db_manager = get_db_manager()
        
        async with db_manager.session() as session:
            result = await session.execute(
                select(DBChannel).where(DBChannel.is_active == True)
            )
            channels = result.scalars().all()
            
            print(f"Found {len(channels)} active channels in database")
            print()
            
            subscribed = 0
            already_subscribed = 0
            failed = 0
            
            for idx, channel in enumerate(channels, 1):
                print(f"[{idx}/{len(channels)}] Processing: {channel.channel_username or channel.channel_id}")
                
                try:
                    # Get channel entity
                    username = channel.channel_username or channel.channel_id
                    if username.startswith("@"):
                        username = username[1:]
                    
                    try:
                        entity = await client.get_entity(username)
                    except ValueError:
                        # Try with channel_id
                        entity = await client.get_entity(int(channel.channel_id))
                    
                    if not isinstance(entity, Channel):
                        print(f"   ⚠️  Not a channel, skipping")
                        failed += 1
                        continue
                    
                    # Try to join
                    try:
                        await client(JoinChannelRequest(entity))
                        print(f"   ✅ Subscribed: {entity.title}")
                        subscribed += 1
                    except Exception as join_error:
                        error_msg = str(join_error).lower()
                        if "already" in error_msg or "user_already_participant" in error_msg:
                            print(f"   ℹ️  Already subscribed: {entity.title}")
                            already_subscribed += 1
                        else:
                            print(f"   ⚠️  Could not subscribe: {join_error}")
                            failed += 1
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                    
                except ChannelPrivateError:
                    print(f"   ❌ Private channel - manual subscription required")
                    failed += 1
                except FloodWaitError as e:
                    print(f"   ⏳ Flood wait: {e.seconds}s, waiting...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    failed += 1
                
                print()
            
            # Summary
            print("=" * 60)
            print("SUBSCRIPTION SUMMARY")
            print("=" * 60)
            print(f"✅ Newly subscribed:     {subscribed}")
            print(f"ℹ️  Already subscribed:   {already_subscribed}")
            print(f"❌ Failed:               {failed}")
            print(f"📊 Total channels:       {len(channels)}")
            print()
            
            if failed > 0:
                print("⚠️  Some channels failed. Possible reasons:")
                print("   - Private channels require manual join")
                print("   - Invalid channel IDs")
                print("   - Rate limiting (try again later)")
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(subscribe_to_all_channels())

