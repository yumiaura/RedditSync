"""Run the trend publisher on a fixed daily schedule (default twice a day).

PUBLISH_TIMES is a comma-separated list of HH:MM slots interpreted in the
PUBLISH_TZ timezone (IANA name, default UTC). Within each slot the tracked
subreddits are staggered PUBLISH_INTERVAL minutes apart (default 60), so
posts go out roughly once an hour instead of all at once.
"""
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

import publish_trends

logger = logging.getLogger("trend_scheduler")
DEFAULT_TIMES = "09:00,21:00"
DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_TZ = "UTC"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def publish_timezone():
    """IANA timezone the PUBLISH_TIMES slots are interpreted in.

    ZoneInfo validates the name, so a typo fails at startup with a clear
    error instead of silently scheduling in the wrong timezone.
    """
    return ZoneInfo(os.getenv("PUBLISH_TZ", DEFAULT_TZ).strip() or DEFAULT_TZ)


def setup_logging():
    """Console logging, plus a rotating file when LOG_FILE is set."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    log_file = os.getenv("LOG_FILE", "").strip()
    if log_file:
        handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(handler)
        logger.info("also logging to %s (rotating, 5 MB x 3)", log_file)


def publish_interval_minutes():
    """Minutes between two subreddits' posts within one PUBLISH_TIMES slot."""
    return int(os.getenv("PUBLISH_INTERVAL", DEFAULT_INTERVAL_MINUTES))


def staggered_schedule(slots, subreddits, interval_minutes):
    """Expand slots × subreddits into per-post times, one hour-ish apart.

    Each subreddit is offset by its position × interval_minutes from the
    slot, so a slot fans out over hours instead of posting everything at
    once. Returns [(hour, minute, subreddit)]; times wrap around midnight.
    """
    schedule = []
    for slot in slots:
        hour, sep, minute = slot.partition(":")
        base = int(hour) * 60 + int(minute or 0)
        for position, subreddit in enumerate(subreddits):
            total = base + position * interval_minutes
            schedule.append(((total // 60) % 24, total % 60, subreddit))
    return schedule


def scheduled_run(subreddit=None):
    try:
        publish_trends.publish_once(
            subreddits=[subreddit] if subreddit else None)
    except Exception as error:
        logger.exception("scheduled publish failed: %s", error)


def touch_heartbeat(heartbeat_file):
    """Refresh the liveness marker the Docker HEALTHCHECK watches."""
    Path(heartbeat_file).touch()


def main():
    setup_logging()
    load_dotenv()
    times = os.getenv("PUBLISH_TIMES", DEFAULT_TIMES)
    slots = [item.strip() for item in times.split(",") if item.strip()]
    subreddits = publish_trends.tracked_subreddits()
    timezone = publish_timezone()
    scheduler = BlockingScheduler(timezone=timezone)
    for hour, minute, subreddit in staggered_schedule(
            slots, subreddits, publish_interval_minutes()):
        scheduler.add_job(
            scheduled_run,
            args=[subreddit],
            trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
            id=f"publish_{hour:02d}{minute:02d}_{subreddit}",
            replace_existing=True,
        )
        logger.info("scheduled daily publish for r/%s at %02d:%02d %s",
                    subreddit, hour, minute, timezone)

    heartbeat_file = os.getenv("HEARTBEAT_FILE", "").strip()
    if heartbeat_file:
        touch_heartbeat(heartbeat_file)
        scheduler.add_job(
            touch_heartbeat,
            args=[heartbeat_file],
            trigger=IntervalTrigger(minutes=1),
            id="heartbeat",
            replace_existing=True,
        )

    def handle_sigterm(signum, frame):
        logger.info("received SIGTERM, shutting down")
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, handle_sigterm)

    logger.info("trend scheduler started")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("interrupted, shutting down")
        scheduler.shutdown(wait=False)
    logger.info("trend scheduler stopped")


if __name__ == "__main__":
    main()
