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
            if '/a/' in parsed.path or '/gallery/' in parsed.path:
                # Это галерея, берем ID первого изображения
                gallery_id = parsed.path.split('/')[-1]
                return f"https://i.imgur.com/{gallery_id}.jpg"
            else:
                # Одиночное изображение
                image_id = parsed.path.split('/')[-1]
                return f"https://i.imgur.com/{image_id}.jpg"
    
    # Handle reddit media and chats
    if 'reddit.com' in parsed.netloc or 'redd.it' in parsed.netloc:
        # Обработка видео
        if 'v.redd.it' in parsed.netloc:
            return url  # Будет обработано в download_file
        
        # Обработка изображений
        if 'i.redd.it' in parsed.netloc:
            # Убираем все параметры запроса
            return f"https://i.redd.it{parsed.path}"
        
        # Convert preview links to direct
        if 'preview.redd.it' in parsed.netloc:
            # Декодируем URL если он закодирован
            decoded_url = url.replace('&amp;', '&')
            if 'width=' in decoded_url:
                # Удаляем параметры размера для получения оригинала
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