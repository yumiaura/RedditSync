"""Post a Reddit meme (photo or album + caption) to a Telegram channel."""
import html
import json

import requests

TELEGRAM_ALBUM_LIMIT = 10

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
              "Gecko/20100101 Firefox/128.0")


def build_caption(title, subreddit, permalink):
    return (
        f"🍝 <b>{html.escape(title)}</b>\n"
        f'<a href="{permalink}">r/{subreddit}</a>'
    )


def call(token, method, payload=None, files=None):
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        data=payload, files=files, timeout=30,
    )
    return response.json()


def send_photo(token, chat_id, image_url, caption):
    result = call(token, "sendPhoto", {
        "chat_id": chat_id,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML",
    })
    if result.get("ok"):
        return result["result"]

    # Telegram could not fetch the URL itself: download and upload the bytes.
    image = requests.get(image_url, headers={"User-Agent": USER_AGENT}, timeout=30)
    image.raise_for_status()
    result = call(token, "sendPhoto",
                  {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                  files={"photo": ("meme.jpg", image.content)})
    if result.get("ok"):
        return result["result"]
    raise RuntimeError(f"sendPhoto failed: {result.get('description')}")


def send_media_group(token, chat_id, image_urls, caption):
    """Post several images as a single album; caption sits on the first image."""
    items = image_urls[:TELEGRAM_ALBUM_LIMIT]

    def build_media(reference_for):
        media = []
        for index, reference in enumerate(reference_for):
            entry = {"type": "photo", "media": reference}
            if index == 0:
                entry["caption"] = caption
                entry["parse_mode"] = "HTML"
            media.append(entry)
        return media

    result = call(token, "sendMediaGroup",
                  {"chat_id": chat_id, "media": json.dumps(build_media(items))})
    if result.get("ok"):
        return result["result"][0]

    # Telegram could not fetch the URLs itself: download and upload the bytes.
    files = {}
    references = []
    for index, url in enumerate(items):
        image = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        image.raise_for_status()
        name = f"photo{index}"
        files[name] = (f"{name}.jpg", image.content)
        references.append(f"attach://{name}")
    result = call(token, "sendMediaGroup",
                  {"chat_id": chat_id, "media": json.dumps(build_media(references))},
                  files=files)
    if result.get("ok"):
        return result["result"][0]
    raise RuntimeError(f"sendMediaGroup failed: {result.get('description')}")
