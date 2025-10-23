"""Database operations for Reddit Sync using SQLAlchemy ORM.

This module provides async database operations using SQLAlchemy ORM.
All functions work with async sessions and provide high-level database
operations for the Reddit Sync application.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.exc import IntegrityError

try:
    from .models import Base, Subscription, News, Media
except ImportError:
    from models import Base, Subscription, News, Media

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url(db_path: str) -> str:
    """Convert file path to SQLite async URL."""
    db_file = Path(db_path).resolve()
    return f"sqlite+aiosqlite:///{db_file}"


class DatabaseManager:
    """Database manager for SQLAlchemy operations."""
    
    def __init__(self, database_url: str):
        """Initialize database manager with database URL."""
        self.database_url = database_url
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    async def init_db(self) -> None:
        """Initialize database with schema and default data."""
        self._engine = create_async_engine(self.database_url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        
        # Create all tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Add default subscription
        async with self.get_session() as session:
            # Check if default subscription exists
            stmt = select(Subscription).where(Subscription.thread_id == "unixporn")
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                default_sub = Subscription(
                    thread_id="unixporn",
                    title="r/unixporn - Unix Customization"
                )
                session.add(default_sub)
                await session.commit()
        
        logger.info("Database initialized successfully")
    
    def get_session(self) -> AsyncSession:
        """Get database session."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._session_factory()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None


async def init_db(db_path: str = 'db.sqlite') -> None:
    """Initialize database with schema and default data.
    
    Args:
        db_path: Path to SQLite database file. Creates if not exists.
    """
    global _engine, _session_factory
    
    database_url = get_database_url(db_path)
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    
    # Create all tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Add default subscription
    async with get_session() as session:
        # Check if default subscription exists
        stmt = select(Subscription).where(Subscription.thread_id == "unixporn")
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if not existing:
            default_sub = Subscription(
                thread_id="unixporn",
                title="r/unixporn - Unix Customization"
            )
            session.add(default_sub)
            await session.commit()
    
    logger.info("Database initialized successfully")


def get_session() -> AsyncSession:
    """Get database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory()


async def close_db() -> None:
    """Close database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_subscriptions() -> List[Dict[str, Any]]:
    """Get list of subscribed threads."""
    async with get_session() as session:
        stmt = select(Subscription)
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()
        
        return [
            {
                "id": sub.id,
                "thread_id": sub.thread_id,
                "title": sub.title,
                "added_at": sub.added_at,
            }
            for sub in subscriptions
        ]


async def add_subscription(thread_id: str, title: str = None) -> None:
    """Add new subscription."""
    async with get_session() as session:
        subscription = Subscription(thread_id=thread_id, title=title)
        session.add(subscription)
        try:
            await session.commit()
            logger.info(f"Added subscription: {thread_id}")
        except IntegrityError:
            await session.rollback()
            logger.debug(f"Subscription already exists: {thread_id}")


async def news_exists(external_id: str) -> bool:
    """Check if news item already exists."""
    async with get_session() as session:
        stmt = select(News).where(News.external_id == external_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def add_news(news_item: Dict[str, Any]) -> None:
    """Add new news item."""
    async with get_session() as session:
        news = News(
            external_id=news_item["external_id"],
            thread_id=news_item.get("thread_id"),
            author=news_item.get("author"),
            created_utc=news_item.get("created_utc"),
            title=news_item.get("title"),
            body=news_item.get("body"),
            media_url=news_item.get("media_url"),
            score=news_item.get("score", 0),
            comment_count=news_item.get("comment_count", 0),
            raw_json=news_item.get("raw_json"),
        )
        session.add(news)
        try:
            await session.commit()
            logger.debug(f"Added news item: {news_item['external_id']}")
        except IntegrityError:
            await session.rollback()
            logger.debug(f"News item already exists: {news_item['external_id']}")


async def update_news_media(external_id: str, media_uid: str) -> None:
    """Update news item with downloaded media UID."""
    async with get_session() as session:
        stmt = select(News).where(News.external_id == external_id)
        result = await session.execute(stmt)
        news = result.scalar_one_or_none()
        
        if news:
            news.media_uid = media_uid
            await session.commit()
            logger.debug(f"Updated media UID for news: {external_id}")


async def update_news_metrics(external_id: str, score: int = None, comment_count: int = None) -> None:
    """Update news item metrics (score and comment count)."""
    async with get_session() as session:
        stmt = select(News).where(News.external_id == external_id)
        result = await session.execute(stmt)
        news = result.scalar_one_or_none()
        
        if news:
            if score is not None:
                news.score = score
            if comment_count is not None:
                news.comment_count = comment_count
            await session.commit()
            logger.debug(f"Updated metrics for news: {external_id} (score={score}, comments={comment_count})")


async def add_media(
    uid_filename: str,
    original_url: str,
    content_type: str,
    size_bytes: int,
    news_external_id: str = None,
) -> None:
    """Add new media record."""
    async with get_session() as session:
        media = Media(
            uid_filename=uid_filename,
            original_url=original_url,
            content_type=content_type,
            size_bytes=size_bytes,
            news_external_id=news_external_id,
        )
        session.add(media)
        try:
            await session.commit()
            logger.debug(f"Added media record: {uid_filename}")
        except IntegrityError:
            await session.rollback()
            logger.debug(f"Media record already exists: {uid_filename}")


async def get_pending_media() -> List[Dict[str, Any]]:
    """Get news items with media_url but no media_uid."""
    async with get_session() as session:
        stmt = select(News).where(
            and_(
                News.media_url.isnot(None),
                News.media_uid.is_(None)
            )
        )
        result = await session.execute(stmt)
        news_items = result.scalars().all()
        
        return [
            {
                "external_id": news.external_id,
                "media_url": news.media_url,
            }
            for news in news_items
        ]


async def get_news_by_thread(thread_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get news items for a specific thread."""
    async with get_session() as session:
        stmt = (
            select(News)
            .where(News.thread_id == thread_id)
            .order_by(News.created_utc.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        news_items = result.scalars().all()
        
        return [
            {
                "id": news.id,
                "external_id": news.external_id,
                "thread_id": news.thread_id,
                "author": news.author,
                "created_utc": news.created_utc,
                "title": news.title,
                "body": news.body,
                "media_url": news.media_url,
                "media_uid": news.media_uid,
                "score": news.score,
                "comment_count": news.comment_count,
                "added_at": news.added_at,
            }
            for news in news_items
        ]


async def get_media_info(uid_filename: str) -> Optional[Dict[str, Any]]:
    """Get media information by UID filename."""
    async with get_session() as session:
        stmt = select(Media).where(Media.uid_filename == uid_filename)
        result = await session.execute(stmt)
        media = result.scalar_one_or_none()
        
        if media:
            return {
                "id": media.id,
                "uid_filename": media.uid_filename,
                "original_url": media.original_url,
                "content_type": media.content_type,
                "size_bytes": media.size_bytes,
                "saved_at": media.saved_at,
            }
        return None