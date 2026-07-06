"""Fetch rising Reddit posts via public Atom feeds — no OAuth required.

Reddit's JSON endpoints reject datacenter IPs, but the RSS/Atom feeds
(/r/<sub>/rising.rss) stay open. They carry no score, so "best trending"
means the feed order Reddit itself assigns to rising posts.
"""
import html
import logging
import re
import time
import xml.etree.ElementTree as ElementTree

import requests

logger = logging.getLogger(__name__)

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
              "Gecko/20100101 Firefox/128.0")
IREDD_RE = re.compile(r"https://i\.redd\.it/[A-Za-z0-9]+\.[A-Za-z0-9]+")
PREVIEW_RE = re.compile(r"https://preview\.redd\.it/([A-Za-z0-9]+\.[A-Za-z0-9]+)")
COMMENTS_RE = re.compile(r"/comments/([a-z0-9]+)/")
GALLERY_RE = re.compile(r"reddit\.com/gallery/[a-z0-9]+")
MEDIA_TILE_RE = re.compile(r'id="media-tile-([a-z0-9]+)-([A-Za-z0-9]+)"')
THING_RE = re.compile(r'<div\b([^>]*\bdata-fullname="t3_[a-z0-9]+"[^>]*)>')
FULLNAME_RE = re.compile(r'data-fullname="t3_([a-z0-9]+)"')
SCORE_RE = re.compile(r'data-score="(-?\d+)"')


def listing_urls(subreddit, listing):
    """Map a listing spec to its (rss_url, html_url) pair on old.reddit.

    A spec is a listing name with an optional time period after a colon:
    "rising" -> /r/<sub>/rising.rss and /r/<sub>/rising/,
    "top:week" -> /r/<sub>/top.rss?t=week and /r/<sub>/top/?t=week.
    """
    name, sep, period = listing.partition(":")
    name = name.strip()
    query = f"?t={period.strip()}" if period.strip() else ""
    base = f"https://old.reddit.com/r/{subreddit}/{name}"
    return f"{base}.rss{query}", f"{base}/{query}"


def get_with_backoff(url, retries=4, pause=35, timeout=20):
    """GET with old.reddit's rate limit in mind: back off and retry on 429."""
    response = None
    for attempt in range(retries):
        if attempt:
            time.sleep(pause * attempt)
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        if response.status_code != 429:
            break
    return response


def fetch_listing(subreddit, listing="rising", retries=4, pause=35):
    rss_url, html_url = listing_urls(subreddit, listing)
    response = get_with_backoff(rss_url, retries, pause, timeout=15)
    response.raise_for_status()
    return parse_feed(subreddit, response.content)


def fetch_rising(subreddit, retries=4, pause=35):
    return fetch_listing(subreddit, "rising", retries, pause)


def parse_feed(subreddit, raw_xml):
    root = ElementTree.fromstring(raw_xml)
    candidates = []
    for entry in root.iter(f"{ATOM}entry"):
        title = entry.findtext(f"{ATOM}title", default="(no title)")
        author = entry.findtext(f"{ATOM}author/{ATOM}name", default="?")
        content = entry.findtext(f"{ATOM}content", default="")
        permalink = ""
        for link in entry.iter(f"{ATOM}link"):
            permalink = link.get("href", "")
        permalink = permalink.replace("old.reddit.com", "reddit.com")
        match = COMMENTS_RE.search(permalink)
        text = html.unescape(content)
        candidates.append({
            "subreddit": subreddit,
            "reddit_id": match.group(1) if match else None,
            "title": title,
            "author": author,
            "permalink": permalink,
            "image_url": extract_image(entry, content),
            "is_gallery": bool(GALLERY_RE.search(text)) or "/gallery/" in permalink,
        })
    if not candidates:
        logger.warning(
            "rising feed for r/%s yielded no entries — empty feed or markup change?",
            subreddit)
    return candidates


def extract_image(entry, content):
    """Return a full-resolution image URL, never a tiny preview thumbnail.

    Reddit's RSS often carries only a 140px preview.redd.it thumbnail (e.g. for
    gallery posts). preview.redd.it/<id>.<ext> maps to the original at
    i.redd.it/<id>.<ext>, so we upgrade previews instead of posting a thumbnail.
    """
    text = html.unescape(content)
    direct = IREDD_RE.search(text)
    if direct:
        return direct.group(0)
    preview = PREVIEW_RE.search(text)
    if preview:
        return f"https://i.redd.it/{preview.group(1)}"
    thumbnail = entry.find(f"{MEDIA}thumbnail")
    if thumbnail is not None:
        preview = PREVIEW_RE.search(thumbnail.get("url", ""))
        if preview:
            return f"https://i.redd.it/{preview.group(1)}"
    return None


def listing_scores(subreddit, listing="rising", retries=4, pause=35):
    """Map reddit_id -> score from an old.reddit listing HTML page.

    The Atom feed carries no score and the JSON API rejects datacenter IPs, but
    the HTML listing marks every post with data-fullname and data-score.
    Returns {} if the page can't be read (callers then publish nothing).
    """
    rss_url, html_url = listing_urls(subreddit, listing)
    response = get_with_backoff(html_url, retries, pause, timeout=20)
    if response is None or response.status_code != 200:
        logger.warning(
            "%s HTML for r/%s not readable (HTTP %s) — publishing nothing",
            listing, subreddit,
            response.status_code if response is not None else "n/a")
        return {}
    scores = {}
    for attrs in THING_RE.findall(response.text):
        fullname = FULLNAME_RE.search(attrs)
        score = SCORE_RE.search(attrs)
        if fullname and score:
            scores[fullname.group(1)] = int(score.group(1))
    if not scores:
        logger.warning(
            "%s HTML for r/%s parsed to zero scores — old.reddit markup change?",
            listing, subreddit)
    return scores


def rising_scores(subreddit, retries=4, pause=35):
    return listing_scores(subreddit, "rising", retries, pause)


def gallery_image_urls(permalink, post_id, retries=4, pause=35):
    """Return every image of a gallery post, in order, at full resolution.

    Reddit's RSS lists only one thumbnail for a gallery, and the JSON API
    rejects datacenter IPs. The old.reddit HTML page stays reachable and marks
    each gallery image with id="media-tile-<post>-<media>", which maps to the
    original at i.redd.it/<media>.<ext>. Returns [] if the page can't be read.
    """
    old_permalink = permalink.replace("://reddit.com", "://old.reddit.com")
    old_permalink = old_permalink.replace("://www.reddit.com", "://old.reddit.com")
    response = get_with_backoff(old_permalink, retries, pause, timeout=20)
    if response is None or response.status_code != 200:
        logger.warning(
            "gallery page %s not readable (HTTP %s)", old_permalink,
            response.status_code if response is not None else "n/a")
        return []
    page = response.text
    urls = []
    seen = set()
    for tile_post, media_id in MEDIA_TILE_RE.findall(page):
        if tile_post != post_id or media_id in seen:
            continue
        seen.add(media_id)
        extension = re.search(re.escape(media_id) + r"\.(jpg|jpeg|png|gif)", page)
        urls.append(f"https://i.redd.it/{media_id}.{extension.group(1) if extension else 'jpg'}")
    if not urls:
        logger.warning(
            "gallery page for post %s parsed to zero images — markup change?", post_id)
    return urls
