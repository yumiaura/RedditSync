"""Run the trend publisher on a fixed daily schedule (default twice a day).

PUBLISH_TIMES is a comma-separated list of HH:MM slots in UTC. Each slot
fires publish_once(), which posts one meme per tracked subreddit.
"""
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

import publish_trends

logger = logging.getLogger("trend_scheduler")
DEFAULT_TIMES = "09:00,21:00"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


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


def scheduled_run():
    try:
        publish_trends.publish_once()
    except Exception as error:
        logger.exception("scheduled publish failed: %s", error)


def touch_heartbeat(heartbeat_file):
    """Refresh the liveness marker the Docker HEALTHCHECK watches."""
    Path(heartbeat_file).touch()


def main():
    setup_logging()
    load_dotenv()
    times = os.getenv("PUBLISH_TIMES", DEFAULT_TIMES)
    scheduler = BlockingScheduler(timezone="UTC")
    for slot in [item.strip() for item in times.split(",") if item.strip()]:
        hour, sep, minute = slot.partition(":")
        scheduler.add_job(
            scheduled_run,
            trigger=CronTrigger(hour=int(hour), minute=int(minute or 0)),
            id=f"publish_{slot}",
            replace_existing=True,
        )
        logger.info("scheduled daily publish at %s UTC", slot)

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
