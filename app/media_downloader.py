"""Media downloader for Reddit Sync.

This module provides functions for downloading and storing media files
from Reddit posts. It handles concurrent downloads, file naming,
and error handling. Uses httpx for async HTTP requests and implements
retry logic for resilience.
"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator
from urllib.parse import urlparse

import aiofiles
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from .utils import generate_uid, extract_file_extension, normalize_media_url
except ImportError:
    from utils import generate_uid, extract_file_extension, normalize_media_url

logger = logging.getLogger(__name__)

# Hosts media may be fetched from. Enforced on the initial URL, on every
# redirect hop and on URLs scraped from og:image/twitter:image metadata.
ALLOWED_MEDIA_HOSTS = (
    'redd.it',
    'reddit.com',
    'redditmedia.com',
    'redditstatic.com',
    'imgur.com',
)

MAX_REDIRECTS = 5

def allowed_media_url(url: str) -> bool:
    """Return True when url is http(s) and points at an allowlisted host."""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    host = (parsed.hostname or '').lower()
    return any(host == allowed or host.endswith('.' + allowed)
               for allowed in ALLOWED_MEDIA_HOSTS)

async def reject_disallowed_url(request: httpx.Request) -> None:
    """httpx request hook: runs for every request including redirect hops."""
    if not allowed_media_url(str(request.url)):
        raise ValueError(f"Blocked URL outside the media host allowlist: {request.url}")

@asynccontextmanager
async def http_client():
    """Context manager for HTTP client."""
    client = httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=MAX_REDIRECTS,
        event_hooks={'request': [reject_disallowed_url]},
    )
    try:
        yield client
    finally:
        await client.aclose()

def ensure_media_dir(media_dir: str) -> Path:
    """Ensure media directory exists and return Path object."""
    path = Path(media_dir)
    path.mkdir(exist_ok=True)
    return path

async def write_stream_to_file(
    response: httpx.Response,
    file_path: Path,
    max_size: int
) -> None:
    """Stream a response body to disk, aborting once it exceeds max_size."""
    bytes_written = 0
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            async for chunk in response.aiter_bytes():
                bytes_written += len(chunk)
                if bytes_written > max_size:
                    raise ValueError(
                        f"File too large: exceeded {max_size} bytes while downloading"
                    )
                await f.write(chunk)
    except BaseException:
        file_path.unlink(missing_ok=True)
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def download_file(
    client: httpx.AsyncClient,
    url: str,
    media_dir: Path,
    max_size: int
) -> Dict[str, Any]:
    """Download a single file with retry on failure."""
    if not allowed_media_url(url):
        raise ValueError(f"Blocked URL outside the media host allowlist: {url}")

    reopen_for_body = False
    async with client.stream('GET', url) as response:
        response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        size = int(response.headers.get('content-length', 0))

        if size > max_size:
            raise ValueError(f"File too large: {size} bytes")

        # Check if this is an HTML page with loader
        if content_type.startswith('text/html'):
            # Check first bytes to determine content type
            content_preview = bytearray()
            async for chunk in response.aiter_bytes():
                content_preview.extend(chunk)
                if len(content_preview) >= 1024:
                    break
            content_preview = bytes(content_preview[:1024])
            if b'<!DOCTYPE html>' in content_preview or b'<html' in content_preview:
                # If this is a loading page, try to get direct link from metadata
                if b'og:image' in content_preview or b'twitter:image' in content_preview:
                    # Extract direct media link
                    direct_url = re.search(b'content="([^"]+)"', content_preview)
                    if direct_url:
                        # Recursively download direct link; the allowlist
                        # check at the top vets the scraped URL too
                        decoded_url = direct_url.group(1).decode()
                        return await download_file(client, decoded_url, media_dir, max_size)
                raise ValueError("Received HTML loading page instead of media content")
            # text/html content-type without HTML markers: still worth
            # saving, but the stream is partially consumed — re-request below
            reopen_for_body = True

        extension = extract_file_extension(url, content_type)
        uid_filename = f"{generate_uid()}.{extension}"
        file_path = media_dir / uid_filename

        if not reopen_for_body:
            await write_stream_to_file(response, file_path, max_size)

    if reopen_for_body:
        async with client.stream('GET', url) as response:
            response.raise_for_status()
            await write_stream_to_file(response, file_path, max_size)

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