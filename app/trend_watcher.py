"""Fetch trending Reddit posts through the OAuth API.

Reddit closed the anonymous doors the publisher used to walk through: the
old.reddit HTML listings and their .rss feeds now answer any logged-out
request with the "Welcome to Reddit" login page, and www.reddit.com/*.json
answers 403. The OAuth API stays open, carries the score and the full gallery
in the same response, and needs one request per listing instead of two.

Credentials come from REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET /
REDDIT_REFRESH_TOKEN; mint a refresh token with tools/1_get_refresh_token.py.
"""
import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
DEFAULT_USER_AGENT = "python:redditsync:v1.0 (trend publisher)"
LISTING_LIMIT = 50
TOKEN_EXPIRY_MARGIN = 60
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif")
GALLERY_EXTENSIONS = {
    "image/jpg": "jpg",
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
}
PREVIEW_RE = re.compile(r"https://preview\.redd\.it/([A-Za-z0-9]+\.[A-Za-z0-9]+)")

# Access token cached between calls for the lifetime of the process.
token_cache = {"value": None, "expires_at": 0.0}


def user_agent():
    return os.getenv("REDDIT_USER_AGENT") or DEFAULT_USER_AGENT


def access_token(force_refresh=False):
    """Return a bearer token, minting a new one when the cached one is stale."""
    now = time.time()
    if not force_refresh and token_cache["value"] and now < token_cache["expires_at"]:
        return token_cache["value"]
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")
    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError(
            "REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET and REDDIT_REFRESH_TOKEN "
            "are required — mint a token with tools/1_get_refresh_token.py")
    response = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"User-Agent": user_agent()},
        timeout=20)
    if response.status_code != 200:
        raise RuntimeError(
            f"token request failed: HTTP {response.status_code} — "
            "the refresh token may have been revoked, re-run "
            "tools/1_get_refresh_token.py --save")
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("token response carried no access_token")
    token_cache["value"] = token
    token_cache["expires_at"] = now + int(payload.get("expires_in", 3600)) - TOKEN_EXPIRY_MARGIN
    return token


def listing_request(subreddit, listing):
    """Map a listing spec to its API path and query parameters.

    A spec is a listing name with an optional time period after a colon:
    "rising" -> /r/<sub>/rising, "top:week" -> /r/<sub>/top?t=week.
    """
    name, sep, period = listing.partition(":")
    params = {"limit": LISTING_LIMIT, "raw_json": 1}
    if period.strip():
        params["t"] = period.strip()
    return f"/r/{subreddit}/{name.strip()}", params


def api_get(path, params, retries=4, pause=35, timeout=20):
    """GET an API path, backing off on 429 and re-minting a rejected token."""
    response = None
    for attempt in range(retries):
        if attempt:
            time.sleep(pause * attempt)
        token = access_token(
            force_refresh=response is not None and response.status_code == 401)
        response = requests.get(
            API_BASE + path,
            params=params,
            headers={"Authorization": f"bearer {token}",
                     "User-Agent": user_agent()},
            timeout=timeout)
        if response.status_code not in (401, 429):
            break
    response.raise_for_status()
    return response.json()


def fetch_listing(subreddit, listing="rising", retries=4, pause=35):
    path, params = listing_request(subreddit, listing)
    return parse_listing(subreddit, api_get(path, params, retries, pause))


def fetch_rising(subreddit, retries=4, pause=35):
    return fetch_listing(subreddit, "rising", retries, pause)


def parse_listing(subreddit, payload):
    """Turn an API listing payload into candidate dicts, in listing order."""
    candidates = []
    for child in payload.get("data", {}).get("children", []):
        post = child.get("data") or {}
        images = extract_images(post)
        candidates.append({
            "subreddit": subreddit,
            "reddit_id": post.get("id"),
            "title": post.get("title") or "(no title)",
            "author": f"/u/{post.get('author', '?')}",
            "permalink": f"https://reddit.com{post.get('permalink', '')}",
            "score": int(post.get("score") or 0),
            "image_url": images[0] if images else None,
            "images": images,
            "is_gallery": bool(post.get("is_gallery")),
        })
    if not candidates:
        logger.warning(
            "listing for r/%s yielded no posts — empty listing or API change?",
            subreddit)
    return candidates


def extract_images(post):
    """Return every image of a post, in order, at full resolution."""
    if post.get("is_gallery"):
        return gallery_images(post)
    single = single_image(post)
    return [single] if single else []


def gallery_images(post):
    """Full-resolution gallery images in the order Reddit lists them.

    media_metadata carries the mime type per media id, and
    i.redd.it/<media_id>.<ext> is the original behind every preview tile.
    """
    metadata = post.get("media_metadata") or {}
    items = (post.get("gallery_data") or {}).get("items") or []
    urls = []
    for item in items:
        media_id = item.get("media_id")
        meta = metadata.get(media_id) or {}
        extension = GALLERY_EXTENSIONS.get(meta.get("m"))
        if media_id and extension:
            urls.append(f"https://i.redd.it/{media_id}.{extension}")
            continue
        source = (meta.get("s") or {}).get("u")
        if source:
            urls.append(upgrade_preview(source))
    if not urls:
        logger.warning("gallery post %s carried no readable images",
                       post.get("id"))
    return urls


def single_image(post):
    """The post's image, never a tiny preview thumbnail; None for text posts."""
    direct = post.get("url_overridden_by_dest") or post.get("url") or ""
    if direct.lower().endswith(IMAGE_SUFFIXES):
        return upgrade_preview(direct)
    previews = (post.get("preview") or {}).get("images") or []
    source = (previews[0].get("source") or {}).get("url") if previews else None
    if source:
        return upgrade_preview(source)
    return None


def upgrade_preview(url):
    """preview.redd.it/<id>.<ext> maps to the original at i.redd.it/<id>.<ext>."""
    match = PREVIEW_RE.match(url)
    return f"https://i.redd.it/{match.group(1)}" if match else url
