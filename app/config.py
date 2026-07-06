"""Configuration loader for Reddit Sync.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = './news.db'
DEFAULT_MEDIA_DIR = './media'


def resolve_repo_path(value: str) -> Path:
    """Resolve a path against the repo root unless it is already absolute.

    Keeps every entry point (sync engine, web UI, tools) on the same file
    regardless of the working directory, matching the PUBLISHED_DB convention.
    """
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def database_path() -> Path:
    """Env-driven SQLite path shared by the sync engine and the web UI."""
    load_dotenv()
    return resolve_repo_path(os.getenv('DB_PATH', DEFAULT_DB_PATH))


def media_dir_path() -> Path:
    """Env-driven media directory shared by the sync engine and the web UI."""
    load_dotenv()
    return resolve_repo_path(os.getenv('MEDIA_DIR', DEFAULT_MEDIA_DIR))


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
        self.db_path = str(database_path())
        self.media_dir = media_dir_path()
        self.max_media_size = int(os.getenv('MAX_MEDIA_SIZE', 50 * 1024 * 1024))  # 50MB
        self.max_concurrent_downloads = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 5))

        # Create database URL for SQLAlchemy
        self.database_url = f"sqlite+aiosqlite:///{self.db_path}"
        
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