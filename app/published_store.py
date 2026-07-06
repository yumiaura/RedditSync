"""Persistent record of already-published Reddit posts, to avoid reposting."""
import os
import sqlite3
import time
from pathlib import Path

DEFAULT_DB = "published.sqlite"


def store_path():
    return Path(os.getenv("PUBLISHED_DB", DEFAULT_DB)).resolve()


def open_store():
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS published (
            reddit_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            permalink TEXT NOT NULL,
            telegram_message_id INTEGER,
            published_at INTEGER NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def is_published(connection, reddit_id):
    row = connection.execute(
        "SELECT 1 FROM published WHERE reddit_id = ?", (reddit_id,)
    ).fetchone()
    return row is not None


def mark_published(connection, reddit_id, subreddit, title, permalink,
                   telegram_message_id):
    connection.execute(
        """
        INSERT OR REPLACE INTO published
            (reddit_id, subreddit, title, permalink,
             telegram_message_id, published_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (reddit_id, subreddit, title, permalink,
         telegram_message_id, int(time.time())),
    )
    connection.commit()
