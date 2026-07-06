"""Fetch rising Reddit posts via public Atom feeds — no OAuth required.

Reddit's JSON endpoints reject datacenter IPs, but the RSS/Atom feeds
(/r/<sub>/rising.rss) stay open. They carry no score, so "best trending"
means the feed order Reddit itself assigns to rising posts.
"""
import html
import re
import time
import xml.etree.ElementTree as ElementTree

import requests

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
              "Gecko/20100101 Firefox/128.0")
IREDD_RE = re.compile(r"https://i\.redd\.it/[A-Za-z0-9]+\.[A-Za-z0-9]+")
PREVIEW_RE = re.compile(r"https://preview\.redd\.it/([A-Za-z0-9]+\.[A-Za-z0-9]+)")
COMMENTS_RE = re.compile(r"/comments/([a-z0-9]+)/")


def fetch_rising(subreddit, retries=4, pause=35):
    response = None
    for attempt in range(retries):
        if attempt:
            time.sleep(pause * attempt)
        response = requests.get(
            f"https://old.reddit.com/r/{subreddit}/rising.rss",
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        if response.status_code != 429:
            break
    response.raise_for_status()
    return parse_feed(subreddit, response.content)


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
        candidates.append({
            "subreddit": subreddit,
            "reddit_id": match.group(1) if match else None,
            "title": title,
            "author": author,
            "permalink": permalink,
            "image_url": extract_image(entry, content),
        })
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
