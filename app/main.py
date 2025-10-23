"""Main entry point for Reddit Sync with scheduler.
"""
import asyncio
import logging
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

# Add current directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from db import DatabaseManager
from reddit_client import reddit_client
import sync_worker as sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Timezone configuration
TIMEZONE = ZoneInfo("UTC")

# Global database manager instance
db_manager = None


async def sync_news_task(max_posts: int = 5):
    """Async task to sync and collect news posts with comments and scores.
    
    Args:
        max_posts: Maximum number of posts to process in this run
    """
    logger.info(f"Starting news sync task (max_posts={max_posts})")
    
    try:
        # Load configuration
        config = Config()
        
        # Use global database manager (should already be initialized)
        global db_manager
        if not db_manager:
            raise RuntimeError("Database manager not initialized")
        
        # Run sync process within Reddit client context
        async with reddit_client(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent,
            refresh_token=config.reddit_refresh_token
        ) as reddit:
            await sync.sync_all(
                reddit=reddit,
                db_manager=db_manager,
                media_dir=config.media_dir,
                max_concurrent=config.max_concurrent_downloads,
                max_posts=max_posts
            )
            logger.info(f"Successfully completed news sync task ({max_posts} posts)")
            
    except Exception as e:
        logger.error(f"News sync task failed: {e}")
        raise


def run_async_task(async_func, *args, **kwargs):
    """Helper function to run async tasks in scheduler."""
    try:
        # Create new event loop for each task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_func(*args, **kwargs))
    except Exception as e:
        logger.error(f"Async task execution failed: {e}")
    finally:
        loop.close()


def main():
    """Main function with scheduler."""
    logging.info("Starting Reddit Sync scheduler...")
    
    # Initialize database before starting scheduler
    logging.info("Initializing database...")
    try:
        config = Config()
        global db_manager
        db_manager = DatabaseManager(config.database_url)
        
        # Run database initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db_manager.init_db())
        loop.close()
        
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        raise
    
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    
    # Schedule the tasks
    scheduler.add_job(
        run_async_task,
        args=[sync_news_task, 5],
        trigger=DateTrigger(run_date=datetime.now(TIMEZONE) + timedelta(seconds=10)),
        max_instances=1,
        coalesce=True,
        id="onstart",
        replace_existing=True,
    )
    
    scheduler.add_job(
        run_async_task,
        args=[sync_news_task, 5],
        trigger=IntervalTrigger(minutes=2),
        max_instances=1,
        coalesce=True,
        id="sync_news",
        replace_existing=True,
    )
    
    scheduler.start()
    logging.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler shut down.")
        
        # Clean up database connections
        if db_manager:
            asyncio.run(db_manager.close())


if __name__ == '__main__':
    main()