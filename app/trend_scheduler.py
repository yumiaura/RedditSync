"""Run the trend publisher on a fixed daily schedule (default twice a day).

PUBLISH_TIMES is a comma-separated list of HH:MM slots in UTC. Each slot
fires publish_once(), which posts one meme per tracked subreddit.
"""
import logging
import os
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

import publish_trends

logger = logging.getLogger("trend_scheduler")
DEFAULT_TIMES = "09:00,21:00"


def scheduled_run():
    try:
        publish_trends.publish_once()
    except Exception as error:
        logger.exception("scheduled publish failed: %s", error)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
    logger.info("trend scheduler started")
    scheduler.start()


if __name__ == "__main__":
    main()
