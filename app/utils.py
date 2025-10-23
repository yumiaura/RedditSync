"""Utility functions for the Reddit sync.
"""
import logging
import re
import uuid
from typing import Optional
from urllib.parse import urlparse

from tenacity import retry, stop_after_attempt, wait_exponential

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
            if '/a/' in parsed.path or '/gallery/' in parsed.path:
                # This is a gallery, take ID of first image
                gallery_id = parsed.path.split('/')[-1]
                return f"https://i.imgur.com/{gallery_id}.jpg"
            else:
                # Single image
                image_id = parsed.path.split('/')[-1]
                return f"https://i.imgur.com/{image_id}.jpg"
    
    # Handle reddit media and chats
    if 'reddit.com' in parsed.netloc or 'redd.it' in parsed.netloc:
        # Video processing
        if 'v.redd.it' in parsed.netloc:
            return url  # Will be processed in download_file
        
        # Image processing
        if 'i.redd.it' in parsed.netloc:
            # Remove all query parameters
            return f"https://i.redd.it{parsed.path}"
        
        # Convert preview links to direct
        if 'preview.redd.it' in parsed.netloc:
            # Decode URL if encoded
            decoded_url = url.replace('&amp;', '&')
            if 'width=' in decoded_url:
                # Remove size parameters to get original
                return re.sub(r'\?.*$', '', decoded_url).replace('preview.redd.it', 'i.redd.it')
            return decoded_url.replace('preview.redd.it', 'i.redd.it')
        
        # Convert reddit.com/media to direct links
        if '/media/' in parsed.path:
            media_id = parsed.path.split('/')[-1]
            return f"https://i.redd.it/{media_id}"
    
    # Remove tracking parameters and queries
    if parsed.path.endswith(('.jpg', '.png', '.gif', '.mp4', '.webm', '.webp')):
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    return url

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def retry_async(coroutine):
    """Retry coroutine with exponential backoff."""
    return await coroutine