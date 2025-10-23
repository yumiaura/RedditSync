"""Main entry point for Reddit Sync - functional style.
"""
import asyncio
import logging
from pathlib import Path
from .config import load_config
from . import db
from .reddit_client import reddit_client
from . import sync_worker as sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize database
        await db.init_db(config['DB_PATH'])
        
        # Run sync process within Reddit client context
        async with reddit_client(
            client_id=config['REDDIT_CLIENT_ID'],
            client_secret=config['REDDIT_CLIENT_SECRET'],
            user_agent=config['REDDIT_USER_AGENT'],
            refresh_token=config['REDDIT_REFRESH_TOKEN']
        ) as reddit:
            await sync.sync_all(
                reddit=reddit,
                db_path=config['DB_PATH'],
                media_dir=config['MEDIA_DIR'],
                max_concurrent=config['MAX_CONCURRENT_DOWNLOADS']
            )
            logger.info("Successfully completed full sync")
            
    except Exception as e:
        logger.error(f"Sync execution failed: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())