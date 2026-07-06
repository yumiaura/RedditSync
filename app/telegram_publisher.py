"""Post a Reddit meme (photo + caption) to a Telegram channel."""
import html

import requests

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
