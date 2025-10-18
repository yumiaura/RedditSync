"""Configuration loader for the Reddit bot.
"""
import os
from dotenv import load_dotenv

def load_config():
    """Load configuration from .env file."""
    load_dotenv()
    
    required = {
        'REDDIT_CLIENT_ID': os.getenv('REDDIT_CLIENT_ID'),
        'REDDIT_CLIENT_SECRET': os.getenv('REDDIT_CLIENT_SECRET'),
        'REDDIT_USER_AGENT': os.getenv('REDDIT_USER_AGENT'),
    }
    
    # Check required variables
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Optional variables with defaults
    config = {
        **required,
        'REDDIT_REFRESH_TOKEN': os.getenv('REDDIT_REFRESH_TOKEN'),
        'DB_PATH': os.getenv('DB_PATH', 'db.sqlite'),
        'MEDIA_DIR': os.getenv('MEDIA_DIR', 'media'),
        'MAX_MEDIA_SIZE': int(os.getenv('MAX_MEDIA_SIZE', 50 * 1024 * 1024)),  # 50MB
        'MAX_CONCURRENT_DOWNLOADS': int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 5))
    }
    
    return config