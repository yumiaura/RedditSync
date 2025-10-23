"""Reddit API client"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, AsyncGenerator, Optional

import praw
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
    try:
        # For galleries take URL of first image from media_metadata
        if hasattr(submission, 'is_gallery') and submission.is_gallery:
            if hasattr(submission, 'media_metadata'):
                for media_id in submission.media_metadata:
                    item = submission.media_metadata[media_id]
                    if 'p' in item and item['p']:
                        # Take image with maximum size
                        largest = max(item['p'], key=lambda x: x.get('x', 0))
                        if 'u' in largest:
                            return largest['u'].replace('preview.redd.it', 'i.redd.it')
                    elif 's' in item and item['s'].get('u'):
                        return item['s']['u'].replace('preview.redd.it', 'i.redd.it')

        # For videos use secure_media
        if submission.is_video and hasattr(submission, 'secure_media'):
            if submission.secure_media and 'reddit_video' in submission.secure_media:
                return submission.secure_media['reddit_video'].get('fallback_url')

        # For regular posts with preview
        if hasattr(submission, 'preview') and 'images' in submission.preview:
            image = submission.preview['images'][0]
            if 'source' in image:
                return image['source']['url'].replace('preview.redd.it', 'i.redd.it')

        # Direct media link
        if hasattr(submission, 'url_overridden_by_dest'):
            return submission.url_overridden_by_dest
        elif hasattr(submission, 'url'):
            return submission.url

    except Exception as e:
        logger.error(f"Error extracting media URL from submission {submission.id}: {e}")
    
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