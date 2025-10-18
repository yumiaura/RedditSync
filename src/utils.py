"""Utility functions for the Reddit bot.
"""
import uuid
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from typing import Optional
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def generate_uid() -> str:
    """Generate a unique identifier."""
    return uuid.uuid4().hex

def extract_file_extension(url: str, content_type: Optional[str] = None) -> str:
    """Extract file extension from URL or content type."""
    # Try to get extension from URL first
    path = urlparse(url).path
    ext = re.search(r'\.(jpg|jpeg|png|gif|mp4|webm|webp)$', path, re.I)
    if ext:
        return ext.group(1).lower()
    
    # Fallback to content type mapping
    if content_type:
        mime_map = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'video/mp4': 'mp4',
            'video/webm': 'webm',
            'image/webp': 'webp'
        }
        return mime_map.get(content_type.lower(), 'bin')
    
    return 'bin'

def normalize_media_url(url: str) -> str:
    """Normalize media URLs (handle imgur, reddit, chats, etc)."""
    if not url:
        return ''
    
    parsed = urlparse(url)
    
    # Convert imgur links to direct
    if 'imgur.com' in parsed.netloc:
        if not url.endswith(('.jpg', '.png', '.gif')):
            return url + '.jpg'
    
    # Handle reddit media and chats
    if 'reddit.com' in parsed.netloc or 'redd.it' in parsed.netloc:
        # Convert chat previews to actual content
        if '/chat' in parsed.path:
            # Extract chat content ID and convert to direct media URL
            chat_id = re.search(r'/chat/([^/]+)', parsed.path)
            if chat_id:
                return f"https://reddit-uploaded-media.s3-accelerate.amazonaws.com/chat/{chat_id.group(1)}"
        # Handle reddit gallery
        elif 'gallery' in parsed.path:
            # Extract gallery ID and get first image
            gallery_id = re.search(r'/gallery/([^/]+)', parsed.path)
            if gallery_id:
                return f"https://i.redd.it/{gallery_id.group(1)}.jpg"
        # Convert preview links to direct media
        elif 'preview.redd.it' in parsed.netloc:
            return url.replace('preview.redd.it', 'i.redd.it')
    
    # Remove tracking parameters and queries that might cause loading screens
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.path.endswith(('.jpg', '.png', '.gif', '.mp4', '.webm', '.webp')):
        return clean_url
    
    return url

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def retry_async(coroutine):
    """Retry coroutine with exponential backoff."""
    return await coroutine