"""Reddit API client for the bot - functional style.
"""
import praw
import logging
from typing import Dict, Any, AsyncGenerator, Optional
import asyncio
from contextlib import asynccontextmanager
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

@asynccontextmanager
async def reddit_client(
    client_id: str,
    client_secret: str,
    user_agent: str,
    refresh_token: Optional[str] = None
):
    """Create and manage Reddit client instance."""
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        refresh_token=refresh_token
    )
    logger.info("Reddit client initialized")
    try:
        yield reddit
    finally:
        # Any cleanup if needed
        pass

def extract_media_url(submission: praw.models.Submission) -> Optional[str]:
    """Extract media URL from submission."""
    if hasattr(submission, 'url_overridden_by_dest'):
        return submission.url_overridden_by_dest
    elif hasattr(submission, 'url'):
        return submission.url
    return None

def submission_to_dict(submission: praw.models.Submission, thread_id: str) -> Dict[str, Any]:
    """Convert Reddit submission to dictionary."""
    return {
        'external_id': submission.id,
        'thread_id': thread_id,
        'author': str(submission.author),
        'created_utc': int(submission.created_utc),
        'title': submission.title,
        'body': submission.selftext,
        'media_url': extract_media_url(submission),
        'raw_json': str(submission)
    }

async def iter_submissions(
    reddit: praw.Reddit,
    thread_id: str,
    limit: int = 100
) -> AsyncGenerator[Dict[str, Any], None]:
    """Iterate over submissions from a subreddit."""
    subreddit = reddit.subreddit(thread_id)
    
    for submission in subreddit.new(limit=limit):
        yield submission_to_dict(submission, thread_id)
        await asyncio.sleep(0.1)  # Prevent hitting rate limits

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_thread_posts(
    reddit: praw.Reddit,
    thread_id: str,
    limit: int = 100
) -> AsyncGenerator[Dict[str, Any], None]:
    """Get latest posts from a thread/subreddit with retry."""
    try:
        async for post in iter_submissions(reddit, thread_id, limit):
            yield post
    except Exception as e:
        logger.error(f"Error fetching posts from {thread_id}: {e}")
        raise