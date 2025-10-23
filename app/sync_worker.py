"""Synchronization functions for the Reddit sync.

This module contains pure functions for synchronizing Reddit content,
including thread posts and media downloads. Each function is focused
on a specific sync task and can be composed to form the complete
sync workflow.
"""
import asyncio
import logging
from typing import Optional, Dict, Any

import praw

try:
    from . import db
    from . import reddit_client as rc
    from . import media_downloader as md
except ImportError:
    import db
    import reddit_client as rc
    import media_downloader as md

logger = logging.getLogger(__name__)

async def sync_thread(
    reddit: praw.Reddit,
    thread_id: str,
    db_manager,
    limit: int = 100
) -> int:
    """Sync posts from a specific thread.
    
    Args:
        reddit: Reddit API client
        thread_id: Thread/subreddit ID to sync
        db_manager: Database manager instance
        limit: Maximum posts to fetch
    
    Returns:
        Number of new posts processed
    """
    logger.info(f"Starting synchronization for thread {thread_id}")
    processed = 0
    
    async for post in rc.get_thread_posts(reddit, thread_id, limit):
        async with db_manager.get_session() as session:
            from sqlalchemy import select
            try:
                from .models import News
            except ImportError:
                from models import News
            
            # Check if news exists
            stmt = select(News).where(News.external_id == post['external_id'])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Add new news
                news = News(
                    external_id=post["external_id"],
                    thread_id=post.get("thread_id"),
                    author=post.get("author"),
                    created_utc=post.get("created_utc"),
                    title=post.get("title"),
                    body=post.get("body"),
                    media_url=post.get("media_url"),
                    score=post.get("score", 0),
                    comment_count=post.get("comment_count", 0),
                    raw_json=post.get("raw_json"),
                )
                session.add(news)
                await session.commit()
                logger.info(f"Successfully saved post {post['external_id']} from thread {thread_id}")
                processed += 1
            else:
                # Update existing news metrics
                existing.score = post.get('score', 0)
                existing.comment_count = post.get('comment_count', 0)
                await session.commit()
    
    logger.info(f"Processed {processed} new posts from thread {thread_id}")
    return processed

async def sync_media_item(
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
            await db.add_media(
                news_external_id=item['external_id'],
                **media_info
            )
            await db.update_news_media(
                item['external_id'],
                media_info['uid_filename']
            )
            logger.info(f"Successfully downloaded media for post {item['external_id']}")
    except Exception as e:
        logger.error(f"Media download failed for post {item['external_id']}: {e}")

async def sync_pending_media(
    media_dir: str = 'media',
    max_concurrent: int = 5
) -> None:
    """Process and download all pending media files."""
    pending = await db.get_pending_media()
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Process media downloads concurrently
    tasks = [
        sync_media_item(media_dir, item, semaphore)
        for item in pending
    ]
    await asyncio.gather(*tasks)

async def sync_all(
    reddit: praw.Reddit,
    db_manager,
    media_dir: str = 'media',
    max_concurrent: int = 5,
    max_posts: Optional[int] = None
) -> None:
    """Synchronize all subscriptions.
    
    Args:
        reddit: Reddit API client
        db_manager: Database manager instance
        media_dir: Directory for storing media files
        max_concurrent: Maximum concurrent downloads
        max_posts: Maximum number of posts to process (None for unlimited)
    """
    total_processed = 0
    
    # Get subscriptions
    async with db_manager.get_session() as session:
        from sqlalchemy import select
        try:
            from .models import Subscription
        except ImportError:
            from models import Subscription
        
        stmt = select(Subscription)
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()
    
    # Sync threads sequentially to avoid rate limits
    for sub in subscriptions:
        if max_posts and total_processed >= max_posts:
            logger.info(f"Reached maximum posts limit ({max_posts}), stopping sync")
            break
            
        try:
            # Calculate remaining posts for this thread
            thread_limit = max_posts - total_processed if max_posts else 100
            processed = await sync_thread(reddit, sub.thread_id, db_manager, limit=thread_limit)
            total_processed += processed
        except Exception as e:
            logger.error(f"Failed to sync {sub.thread_id}: {e}")

    # Download media concurrently (simplified for now)
    # await sync_pending_media(media_dir, max_concurrent)
    
    logger.info(f"Total sync completed: {total_processed} posts processed")