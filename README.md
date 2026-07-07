# Reddit Sync

> 🤖 **This project powers a live Telegram channel** — twice a day it posts the
> best rising memes from tracked subreddits.
> **Follow it here → [t.me/humorfromyumi](https://t.me/humorfromyumi)**

A Python application that watches Reddit, publishes trending posts to a Telegram
channel, and (optionally) archives threads and their media into a local SQLite
database.

There are two independent parts, and you can run either on its own:

1. **Trend auto-publisher** — the piece that feeds the Telegram channel. Reads
   rising posts from public Atom feeds (no OAuth), picks the best not-yet-posted
   item with an image from each tracked subreddit, and posts photo + caption to
   the channel on a schedule. **No Reddit API credentials required.**
2. **Sync engine** — the original archiver: OAuth2 Reddit client, background
   scheduler, media downloader, SQLAlchemy storage and a Flask browser UI.

---

## 📣 Trend auto-publisher (Telegram channel)

### How it works

- Fetches `/r/<subreddit>/rising.rss` for every subreddit in `TREND_SUBREDDITS`.
  Reddit's JSON API rejects datacenter IPs, but the Atom feeds stay open, so the
  publisher needs **no OAuth** — only a Telegram bot token.
- "Best trending" = the order Reddit itself assigns to rising posts. The first
  post that has an image, a score of at least `MIN_SCORE`, and has not been
  published yet is chosen (scores come from the old.reddit HTML listing).
- If rising has nothing above the threshold, the publisher walks the
  `TREND_LISTINGS` chain (default `rising,top:week`), so a slow subreddit
  still gets the week's best post instead of silence.
- Posts **photo + caption** (title + `r/<subreddit>` link) to the channel.
  Gallery posts go out as a single **album** with every image at full resolution.
- A SQLite store (`published.sqlite`) remembers every published post id and its
  Telegram `message_id`, so nothing is ever posted twice.
- One post per tracked subreddit per run. With three subreddits on the default
  twice-a-day schedule, that's up to **six posts per day**.
- Within a slot the subreddits are staggered `PUBLISH_INTERVAL` minutes apart
  (default 60), so the channel gets roughly one post per hour instead of a
  burst of three.

### Configuration

Add these to your `.env` (see `env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_TOKEN` | Bot token from @BotFather | *Required* |
| `TELEGRAM_CHANNEL_ID` | Target channel id (e.g. `-1001234567890`) | *Required* |
| `TREND_SUBREDDITS` | Comma-separated subreddits to watch | `ProgrammerHumor` |
| `MIN_SCORE` | Minimum score (upvotes) per published post | `500` |
| `TREND_LISTINGS` | Listing chain tried in order (`name[:period]`) | `rising,top:week` |
| `PUBLISH_TIMES` | Comma-separated `HH:MM` slots in `PUBLISH_TZ` | `09:00,21:00` |
| `PUBLISH_TZ` | IANA timezone for the publish slots (e.g. `Europe/Lisbon`) | `UTC` |
| `PUBLISH_INTERVAL` | Minutes between subreddits within a slot | `60` |
| `PUBLISHED_DB` | Path to the dedup SQLite store | `./data/published.sqlite` |

### Running

```bash
# One-off run: posts one meme per tracked subreddit
python app/publish_trends.py

# Preview only — select and log candidates without posting
python app/publish_trends.py --dry-run

# Run the scheduler in the foreground (posts at PUBLISH_TIMES)
python app/trend_scheduler.py

# Record an already-posted meme so it is never reposted
python tools/backfill_published.py
```

### Docker (recommended for the channel)

The container runs the scheduler and keeps the dedup store on a mounted volume:

```bash
docker compose up --build -d
docker compose logs -f
```

---

## 🗄️ Sync engine (optional archiver)

### Prerequisites

- Python 3.11 or higher
- Reddit API credentials (client id and secret) — only for the sync engine

### Installation

```bash
git clone https://github.com/yumiaura/RedditSync.git
cd RedditSync

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set up Reddit API credentials:

```bash
# Interactive token setup
python tools/1_get_refresh_token.py --save

# Verify the environment configuration
python tools/2_check_env.py
```

### Running

```bash
# Sync application with background scheduler
python app/main.py

# Web interface (optional)
cd web && python app.py
```

The web interface starts with the Flask debug server **disabled**; set
`FLASK_DEBUG=1` only for local development. For anything reachable from the
network, run it behind a real WSGI server instead, e.g.
`gunicorn -w 2 -b 127.0.0.1:5000 web.app:app`.

The sync engine uses **SQLAlchemy 2.0** (async, via `aiosqlite`) over three
tables — `subscriptions`, `news`, `media` — with a background scheduler that
performs an initial sync shortly after launch and a regular sync every two
minutes.

---

## 📁 Project structure

```
RedditSync/
├── app/
│   ├── main.py               # Sync-engine entry point (scheduler)
│   ├── config.py             # Configuration for the sync engine
│   ├── db.py                 # SQLAlchemy database operations
│   ├── models.py             # SQLAlchemy models
│   ├── reddit_client.py      # OAuth2 Reddit client (praw)
│   ├── media_downloader.py   # Media download
│   ├── sync_worker.py        # Sync orchestration
│   ├── utils.py              # Utilities
│   ├── trend_watcher.py      # Rising RSS reader (no OAuth)
│   ├── telegram_publisher.py # Telegram photo posting
│   ├── published_store.py    # SQLite dedup store
│   ├── publish_trends.py     # Trend publisher orchestrator
│   └── trend_scheduler.py    # Twice-daily scheduler for the publisher
├── tools/
│   ├── 1_get_refresh_token.py
│   ├── 2_check_env.py
│   └── backfill_published.py # Mark an already-posted meme as published
├── web/                      # Flask browser UI (optional)
├── docs/                     # Documentation
├── Dockerfile
├── docker-compose.yml
├── env.example
├── requirements.txt
└── CHANGELOG.md
```

## 🧪 Tests

The suite covers the trend-publisher: feed/HTML parsers against saved
fixtures, the dedup store, caption building and post selection. It runs
offline in a couple of seconds:

```bash
pip install -r requirements-dev.txt
pytest
```

Linting and tests run in CI on every push and pull request.

## 🛡️ Error handling & resilience

- Rising feeds are rate-limited by Reddit; the watcher backs off and retries on
  HTTP 429, and paces requests between subreddits.
- Telegram posting falls back to uploading the image bytes if Telegram cannot
  fetch the URL itself.
- The dedup store guarantees a post is never sent to the channel twice.
- Comprehensive logging (timestamp, level, logger name) for debugging.

## 📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
