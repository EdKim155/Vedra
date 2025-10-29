#!/usr/bin/env python
"""Check posts in database"""
import sys
sys.path.insert(0, "/root/cars-bot/src")

from cars_bot.database.connection import get_session_factory
from cars_bot.database.models.post import Post
from sqlalchemy import select

def main():
    SessionFactory = get_session_factory()
    session = SessionFactory()
    
    posts = session.execute(select(Post).order_by(Post.id.desc()).limit(5)).scalars().all()
    
    print("=== LAST 5 POSTS ===")
    for post in posts:
        brand = post.car_data.brand if post.car_data else "N/A"
        model = post.car_data.model if post.car_data else ""
        print(f"\nPost ID: {post.id}")
        print(f"  Brand/Model: {brand} {model}")
        print(f"  message_ids: {post.message_ids}")
        print(f"  media_files: {post.media_files}")
        print(f"  original_message_link: {post.original_message_link}")
        has_media = bool(post.message_ids) or bool(post.media_files)
        print(f"  has media: {has_media}")
    
    session.close()

if __name__ == "__main__":
    main()


