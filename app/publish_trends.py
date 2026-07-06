"""Publish the best unsent rising post from each tracked subreddit.

One run posts at most one photo per subreddit in TREND_SUBREDDITS, so two
tracked subreddits plus a twice-daily schedule yields four posts per day.
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

import published_store
import telegram_publisher
import trend_watcher

logger = logging.getLogger("trend_publisher")
DEFAULT_SUBREDDITS = "ProgrammerHumor"
DEFAULT_MIN_SCORE = 1000
RATE_LIMIT_PAUSE = 30


def tracked_subreddits():
    raw = os.getenv("TREND_SUBREDDITS", DEFAULT_SUBREDDITS)
    return [name.strip() for name in raw.split(",") if name.strip()]


def min_score():
    return int(os.getenv("MIN_SCORE", DEFAULT_MIN_SCORE))


def pick_unsent(connection, candidates, scores, threshold):
    for candidate in candidates:
        if not candidate["reddit_id"] or not candidate["image_url"]:
            continue
        if scores.get(candidate["reddit_id"], 0) < threshold:
            continue
        if published_store.is_published(connection, candidate["reddit_id"]):
            continue
        return candidate
    return None


def publish_once(dry_run=False):
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHANNEL_ID")
    if not token or not chat_id:
        raise SystemExit("TELEGRAM_TOKEN and TELEGRAM_CHANNEL_ID are required")

    connection = published_store.open_store()
    published = []
    try:
        for position, subreddit in enumerate(tracked_subreddits()):
            if position:
                time.sleep(RATE_LIMIT_PAUSE)  # respect Reddit's RSS rate limit
            threshold = min_score()
            try:
                candidates = trend_watcher.fetch_rising(subreddit)
                scores = trend_watcher.rising_scores(subreddit)
            except Exception as error:
                logger.error("r/%s: could not fetch rising: %s", subreddit, error)
                continue
            choice = pick_unsent(connection, candidates, scores, threshold)
            if not choice:
                logger.info("r/%s: no unposted image post with score >= %d",
                            subreddit, threshold)
                continue
            score = scores.get(choice["reddit_id"], 0)
            caption = telegram_publisher.build_caption(
                choice["title"], subreddit, choice["permalink"])
            images = [choice["image_url"]]
            if choice.get("is_gallery"):
                gallery = trend_watcher.gallery_image_urls(
                    choice["permalink"], choice["reddit_id"])
                if len(gallery) > 1:
                    images = gallery
            if dry_run:
                logger.info("r/%s: would publish '%s' (%s), score %d, %d image(s)",
                            subreddit, choice["title"], choice["reddit_id"],
                            score, len(images))
                continue
            if len(images) > 1:
                result = telegram_publisher.send_media_group(
                    token, chat_id, images, caption)
            else:
                result = telegram_publisher.send_photo(
                    token, chat_id, images[0], caption)
            message_id = result["message_id"]
            published_store.mark_published(
                connection, choice["reddit_id"], subreddit,
                choice["title"], choice["permalink"], message_id)
            logger.info("r/%s: published '%s' (score %d) as message_id=%s",
                        subreddit, choice["title"], score, message_id)
            published.append((subreddit, choice["title"], message_id))
    finally:
        connection.close()
    return published


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="Publish trending Reddit memes")
    parser.add_argument("--dry-run", action="store_true",
                        help="select and log candidates without posting")
    arguments = parser.parse_args()
    publish_once(dry_run=arguments.dry_run)


if __name__ == "__main__":
    main()
