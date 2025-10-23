"""SQLAlchemy models for Reddit Sync.

This module defines the database models using SQLAlchemy ORM.
Models include Subscription, News, and Media tables with proper
relationships and constraints.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


class Subscription(Base):
    """Reddit thread/subreddit subscription model."""
    
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to news items
    news_items: Mapped[list["News"]] = relationship(
        "News", back_populates="subscription", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, thread_id='{self.thread_id}')>"


class News(Base):
    """Reddit news/post model."""
    
    __tablename__ = "news"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thread_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("subscriptions.thread_id")
    )
    author: Mapped[Optional[str]] = mapped_column(String(255))
    created_utc: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(Text)
    body: Mapped[Optional[str]] = mapped_column(Text)
    media_url: Mapped[Optional[str]] = mapped_column(Text)
    media_uid: Mapped[Optional[str]] = mapped_column(String(255))
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="news_items"
    )
    media: Mapped[Optional["Media"]] = relationship(
        "Media", back_populates="news_item", uselist=False
    )
    
    def __repr__(self) -> str:
        return f"<News(id={self.id}, external_id='{self.external_id}')>"


class Media(Base):
    """Downloaded media file model."""
    
    __tablename__ = "media"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    uid_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_url: Mapped[Optional[str]] = mapped_column(Text)
    content_type: Mapped[Optional[str]] = mapped_column(String(255))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Optional relationship to news item (if we want to track which news item this media belongs to)
    news_external_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("news.external_id"), unique=True
    )
    news_item: Mapped[Optional["News"]] = relationship(
        "News", back_populates="media"
    )
    
    def __repr__(self) -> str:
        return f"<Media(id={self.id}, uid_filename='{self.uid_filename}')>"