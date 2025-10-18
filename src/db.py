"""Database operations for the Reddit bot.

This module provides pure functions for database operations,
including initialization, querying, and data manipulation.
All functions take the database path as their first parameter
to maintain stateless operation.
"""
import aiosqlite
import logging
from pathlib import Path
from typing import List, Dict, Any, AsyncContextManager

logger = logging.getLogger(__name__)

async def init_db(db_path: str = 'db.sqlite') -> None:
    """Initialize database with schema and default data.
    
    Args:
        db_path: Path to SQLite database file. Creates if not exists.
    """
    schema_file = Path('db_schema.sql').read_text()
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(schema_file)
        await db.commit()
    logger.info("Database initialized successfully")

def get_connection(db_path: str) -> AsyncContextManager[aiosqlite.Connection]:
    """Get database connection context manager."""
    return aiosqlite.connect(db_path)

async def get_subscriptions(db_path: str) -> List[Dict[str, Any]]:
    """Get list of subscribed threads."""
    async with get_connection(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM subscriptions') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def add_subscription(db_path: str, thread_id: str, title: str = None) -> None:
    """Add new subscription."""
    async with get_connection(db_path) as db:
        await db.execute(
            'INSERT OR IGNORE INTO subscriptions (thread_id, title) VALUES (?, ?)',
            (thread_id, title)
        )
        await db.commit()

async def news_exists(db_path: str, external_id: str) -> bool:
    """Check if news item already exists."""
    async with get_connection(db_path) as db:
        async with db.execute(
            'SELECT 1 FROM news WHERE external_id = ?', 
            (external_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return bool(result)

async def add_news(db_path: str, news_item: Dict[str, Any]) -> None:
    """Add new news item."""
    async with get_connection(db_path) as db:
        await db.execute('''
            INSERT INTO news (
                external_id, thread_id, author, created_utc,
                title, body, media_url, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            news_item['external_id'],
            news_item['thread_id'],
            news_item['author'],
            news_item['created_utc'],
            news_item['title'],
            news_item['body'],
            news_item['media_url'],
            news_item.get('raw_json')
        ))
        await db.commit()

async def update_news_media(db_path: str, external_id: str, media_uid: str) -> None:
    """Update news item with downloaded media UID."""
    async with get_connection(db_path) as db:
        await db.execute(
            'UPDATE news SET media_uid = ? WHERE external_id = ?',
            (media_uid, external_id)
        )
        await db.commit()

async def add_media(
    db_path: str, 
    uid_filename: str, 
    original_url: str, 
    content_type: str, 
    size_bytes: int
) -> None:
    """Add new media record."""
    async with get_connection(db_path) as db:
        await db.execute('''
            INSERT INTO media (
                uid_filename, original_url, content_type, size_bytes
            ) VALUES (?, ?, ?, ?)
        ''', (uid_filename, original_url, content_type, size_bytes))
        await db.commit()

async def get_pending_media(db_path: str) -> List[Dict[str, Any]]:
    """Get news items with media_url but no media_uid."""
    async with get_connection(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT external_id, media_url 
            FROM news 
            WHERE media_url IS NOT NULL 
            AND media_uid IS NULL
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]