"""Synchronization functions for the Reddit bot.

This module contains pure functions for synchronizing Reddit content,
including thread posts and media downloads. Each function is focused
on a specific sync task and can be composed to form the complete
sync workflow.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import praw
import db
import reddit_client as rc
import media_downloader as md

logger = logging.getLogger(__name__)

async def sync_thread(
    reddit: praw.Reddit,
    db_path: str,
    thread_id: str,
    limit: int = 100
) -> None:
    """Sync posts from a specific thread."""
    logger.info(f"Starting synchronization for thread {thread_id}")
    
    async for post in rc.get_thread_posts(reddit, thread_id, limit):
        if not await db.news_exists(db_path, post['external_id']):
            await db.add_news(db_path, post)
            logger.info(f"Successfully saved post {post['external_id']} from thread {thread_id}")

async def sync_media_item(
    db_path: str,
    media_dir: str,
    item: Dict[str, Any],
    semaphore: asyncio.Semaphore
) -> None:
    """Download and store a single media item."""
    try:
        media_info = await md.download_media(
            item['media_url'],
            media_dir=media_dir,
            semaphore=semaphore
        )
        if media_info:
            await db.add_media(db_path, **media_info)
            await db.update_news_media(
                db_path,
                item['external_id'],
                media_info['uid_filename']
            )
            logger.info(f"Successfully downloaded media for post {item['external_id']}")
    except Exception as e:
        logger.error(f"Media download failed for post {item['external_id']}: {e}")

async def sync_pending_media(
    db_path: str,
    media_dir: str = 'media',
    max_concurrent: int = 5
) -> None:
    """Process and download all pending media files."""
    pending = await db.get_pending_media(db_path)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Process media downloads concurrently
    tasks = [
        sync_media_item(db_path, media_dir, item, semaphore)
        for item in pending
    ]
    await asyncio.gather(*tasks)

async def sync_all(
    reddit: praw.Reddit,
    db_path: str,
    media_dir: str = 'media',
    max_concurrent: int = 5
) -> None:
    """Synchronize all subscriptions."""
    subscriptions = await db.get_subscriptions(db_path)
    
    # Sync threads sequentially to avoid rate limits
    for sub in subscriptions:
        try:
            await sync_thread(reddit, db_path, sub['thread_id'])
        except Exception as e:
            logger.error(f"Failed to sync {sub['thread_id']}: {e}")

    # Download media concurrently
    await sync_pending_media(db_path, media_dir, max_concurrent)