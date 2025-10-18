# Reddit Media Bot

A Python bot that monitors Reddit threads, downloads media content, and stores everything in a local SQLite database.

## Features

- Monitors subreddits for new posts
- Downloads media content (images, videos)
- Stores everything in SQLite database
- Supports concurrent media downloads
- Default subscription to r/unixporn

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yumiaura/RedditBot.git
cd RedditBot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Reddit API credentials:
```bash
# Run the token retrieval script
python tools/1_get_refresh_token.py --save

# Verify environment setup
python tools/2_check_env.py
```

## Configuration

Create a `.env` file based on `env.example`:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT="python:mybot:v1.0 (by /u/username)"
REDDIT_REFRESH_TOKEN=your_refresh_token

# Optional settings
DB_PATH=db.sqlite
MEDIA_DIR=media
MAX_MEDIA_SIZE=52428800  # 50MB
MAX_CONCURRENT_DOWNLOADS=5
```

## Usage

1. Run the bot:
```bash
python -m src.main
```

The bot will:
- Initialize the database if needed
- Start monitoring configured subreddits
- Download media from new posts
- Store everything in the SQLite database

## Project Structure

```
redditbot/
├── docs/
│   ├── spec.md              # Technical specification
│   └── auth_instructions.md # Authentication guide
├── src/
│   ├── main.py             # Entry point
│   ├── config.py           # Configuration loader
│   ├── db.py              # Database operations
│   ├── reddit_client.py   # Reddit API wrapper
│   ├── media_downloader.py # Media handling
│   ├── utils.py           # Utilities
│   └── workers/
│       └── sync_worker.py  # Sync orchestration
├── tools/
│   ├── 1_get_refresh_token.py # OAuth2 setup
│   └── 2_check_env.py        # Environment checker
├── media/                    # Downloaded files
├── requirements.txt          # Dependencies
└── db_schema.sql            # Database schema
```

## Database Schema

The bot uses three main tables:
- `subscriptions`: List of monitored subreddits
- `news`: Posts and comments with metadata
- `media`: Downloaded media files information

## Error Handling

- Network errors are retried with exponential backoff
- Large files are skipped (configurable limit)
- All errors are logged for debugging
