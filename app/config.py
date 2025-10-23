"""Configuration loader for Reddit Sync.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration class for Reddit Sync."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        load_dotenv()
        
        # Required variables
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.reddit_user_agent = os.getenv('REDDIT_USER_AGENT')
        
        # Check required variables
        required = {
            'REDDIT_CLIENT_ID': self.reddit_client_id,
            'REDDIT_CLIENT_SECRET': self.reddit_client_secret,
            'REDDIT_USER_AGENT': self.reddit_user_agent,
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Optional variables with defaults
        self.reddit_refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
        self.db_path = os.getenv('DB_PATH', 'db.sqlite')
        self.media_dir = Path(os.getenv('MEDIA_DIR', 'media'))
        self.max_media_size = int(os.getenv('MAX_MEDIA_SIZE', 50 * 1024 * 1024))  # 50MB
        self.max_concurrent_downloads = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 5))
        
        # Create database URL for SQLAlchemy
        db_file = Path(self.db_path).resolve()
        self.database_url = f"sqlite+aiosqlite:///{db_file}"
        
        # Ensure media directory exists
        self.media_dir.mkdir(exist_ok=True)


def load_config():
    """Load configuration from .env file (legacy function for compatibility)."""
    config = Config()
    return {
        'REDDIT_CLIENT_ID': config.reddit_client_id,
        'REDDIT_CLIENT_SECRET': config.reddit_client_secret,
        'REDDIT_USER_AGENT': config.reddit_user_agent,
        'REDDIT_REFRESH_TOKEN': config.reddit_refresh_token,
        'DB_PATH': config.db_path,
        'MEDIA_DIR': str(config.media_dir),
        'MAX_MEDIA_SIZE': config.max_media_size,
        'MAX_CONCURRENT_DOWNLOADS': config.max_concurrent_downloads
    }