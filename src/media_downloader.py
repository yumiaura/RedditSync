"""Media downloader for the Reddit bot.

This module provides functions for downloading and storing media files
from Reddit posts. It handles concurrent downloads, file naming,
and error handling. Uses httpx for async HTTP requests and implements
retry logic for resilience.
"""
import asyncio
import aiofiles
import httpx
import logging
import os
from pathlib import Path
import re
from typing import Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from utils import generate_uid, extract_file_extension, normalize_media_url
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

@asynccontextmanager
async def http_client():
    """Context manager for HTTP client."""
    client = httpx.AsyncClient(follow_redirects=True)
    try:
        yield client
    finally:
        await client.aclose()

def ensure_media_dir(media_dir: str) -> Path:
    """Ensure media directory exists and return Path object."""
    path = Path(media_dir)
    path.mkdir(exist_ok=True)
    return path

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def download_file(
    client: httpx.AsyncClient,
    url: str,
    media_dir: Path,
    max_size: int
) -> Dict[str, Any]:
    """Download a single file with retry on failure."""
    async with client.stream('GET', url) as response:
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        size = int(response.headers.get('content-length', 0))
        
        if size > max_size:
            raise ValueError(f"File too large: {size} bytes")
        
        # Проверяем, не является ли это HTML страницей с загрузчиком
        if content_type.startswith('text/html'):
            # Проверяем первые байты для определения типа контента
            content_preview = await response.aread(1024)
            if b'<!DOCTYPE html>' in content_preview or b'<html' in content_preview:
                # Если это страница загрузки, пробуем получить прямую ссылку из метаданных
                if b'og:image' in content_preview or b'twitter:image' in content_preview:
                    # Извлекаем прямую ссылку на медиа
                    direct_url = re.search(b'content="([^"]+)"', content_preview)
                    if direct_url:
                        # Рекурсивно загружаем прямую ссылку
                        return await download_file(client, direct_url.group(1).decode(), media_dir, max_size)
                raise ValueError("Received HTML loading page instead of media content")
        
        extension = extract_file_extension(url, content_type)
        uid_filename = f"{generate_uid()}.{extension}"
        file_path = media_dir / uid_filename
        
        # Сбрасываем позицию если мы читали контент для проверки
        if response.num_bytes_downloaded:
            await response.aclose()
            response = await client.stream('GET', url)
        
        async with aiofiles.open(file_path, 'wb') as f:
            async for chunk in response.aiter_bytes():
                await f.write(chunk)
        
        return {
            'uid_filename': uid_filename,
            'original_url': url,
            'content_type': content_type,
            'size_bytes': os.path.getsize(file_path)
        }

async def download_media(
    url: str,
    media_dir: str = 'media',
    max_size: int = 50 * 1024 * 1024,
    semaphore: asyncio.Semaphore = None
) -> Optional[Dict[str, Any]]:
    """Download media file and return metadata."""
    url = normalize_media_url(url)
    if not url:
        return None

    if semaphore is None:
        semaphore = asyncio.Semaphore(5)

    media_path = ensure_media_dir(media_dir)
    
    try:
        async with semaphore, http_client() as client:
            return await download_file(client, url, media_path, max_size)
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return None

async def download_many(
    urls: list[str],
    media_dir: str = 'media',
    max_size: int = 50 * 1024 * 1024,
    max_concurrent: int = 5
) -> AsyncGenerator[tuple[str, Optional[Dict[str, Any]]], None]:
    """Download multiple media files concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def download_one(url: str):
        result = await download_media(url, media_dir, max_size, semaphore)
        return url, result
    
    tasks = [download_one(url) for url in urls]
    for task in asyncio.as_completed(tasks):
        yield await task