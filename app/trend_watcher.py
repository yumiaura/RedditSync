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
IMAGE_RE = re.compile(r'href="(https://i\.redd\.it/[^"]+)"')
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
    match = IMAGE_RE.search(html.unescape(content))
    if match:
        return match.group(1)
    thumbnail = entry.find(f"{MEDIA}thumbnail")
    if thumbnail is not None:
        return thumbnail.get("url")
    return None
