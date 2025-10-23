# Reddit Sync Technical Specification and Architecture

**Goal**: Implement a Python application that connects to the Reddit API with read-only permissions, periodically (or on-demand) fetches up to 100 latest messages from subscribed threads, and saves new posts to a local SQLite database. The application also downloads media files from links and saves them to a `media/` folder, while storing the reference to the downloaded file (generated uid) in the `news` table.

## Key Requirements:
- All credentials and configuration parameters in `.env` file (example in `env.example`)
- Authentication: application uses OAuth2 with read permissions (scope: read, maybe identity if needed)
- Database contains tables: `subscriptions`, `news`, `media`
- For each subscription, application fetches up to 100 latest comments/posts (in thread) and adds only new ones to `news`
- Media (from `news.media_url`) are downloaded and saved to `media/` with unique uid filename; `media` table stores uid -> original name/type mapping

## Contract (inputs/outputs):
- **Inputs**: `.env` file with credentials (CLIENT_ID, CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD or refresh token flow), list of threads in `subscriptions` table.
- **Outputs**: updated SQLite database (`db.sqlite`), downloaded files in `media/`.
- **Errors**: network errors, authentication errors; log and retry with exponential backoff.

## Architecture — Brief Overview:

### Components:
- **main.py** — entry point; initializes config, logger and starts synchronization.
- **reddit_client.py** — wrapper for Reddit API (pagination, getting 100 latest messages for thread).
- **db.py** — SQLite layer: schema initialization, functions for reading `subscriptions`, checking news existence, inserting into `news`, `media`.
- **media_downloader.py** — file downloading (parallel, concurrency limit), uid generation for filenames.
- **sync_worker.py** — orchestrates the cycle: reads subscriptions, calls reddit_client for each, filters new items and saves.
- **config.py** — loads `.env` and validates variables.
- **utils.py** — utilities (uid generation, retry decorator, link normalization).

### Data Flow:
1. main -> config -> db
2. db: read `subscriptions` (list of threads, e.g., `thread_fullname` or `submission id`)
3. reddit_client: for each thread get items (up to 100) — posts/comments
4. sync_worker: for each item check if exists in `news` (by external id), if not — insert record (including media_url if present)
5. media_downloader: for new records with links downloads files, generates uid filename and adds record to `media`.

## Database Structure (example SQL):

```sql
-- subscriptions: list of threads we're following
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL UNIQUE,
    title TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- news: all news / items
CREATE TABLE news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE, -- id from Reddit (e.g. t1_... for comment or t3_... for post)
    thread_id TEXT, -- foreign key to subscriptions.thread_id
    author TEXT,
    created_utc INTEGER,
    title TEXT,
    body TEXT,
    media_url TEXT, -- original link
    media_uid TEXT, -- filename in media/ folder if downloaded
    raw_json TEXT, -- optional: full record in json
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- media: information about downloaded files
CREATE TABLE media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid_filename TEXT NOT NULL UNIQUE,
    original_url TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Duplicate Validation:
- Check `news.external_id` uniqueness before insertion. For additional safety, you can hash content and save hash to filter identical texts with different ids.

## Implementation Details:
- Use `praw` library or `httpx` + `requests` directly. PRAW simplifies work but requires OAuth configuration. I recommend `praw` for stability and simplicity.
- For media downloading — `httpx` with concurrency limit via `asyncio` or `concurrent.futures.ThreadPoolExecutor`.
- UID for files: use `uuid4().hex` + original file extension (if known) or content-type -> extension map.
- Logging: use `logging` with rotation (RotatingFileHandler) and DEBUG level during development.
- Retry: wrap network calls in retry with exponential backoff (e.g., tenacity or custom decorator).

## Runtime Workflow:
1. **Startup**: main loads `.env`, initializes DB (if needed), creates `media/` folder.
2. **Read subscriptions** from `subscriptions` table.
3. **For each subscription** get 100 latest items via reddit_client.
4. **Filter** already existing records by `external_id`.
5. **Insert** new ones into `news` (with media_url if present).
6. **Start media download** for new records, write `media_uid` to `news` and create record in `media`.

## Critical Points and Edge Cases:
- **Reddit API rate limits**: limit request frequency, use backoff on 429/5xx.
- **Third-party file hosting links** (imgur, reddit media, gfycat): support redirects and various content-types.
- **Large files**: limit maximum download size.
- **Interruption during writing**: use transactions for atomic inserts and updates.

## Monitoring and Operations:
- Logs and metrics (counter of new records, download errors).
- Manual synchronization capability for single thread.

## Additional Features (optional):
- Web API for viewing news.
- Notifications (email/webhook) for new records.

---
File created: brief specification and architecture. Next step — instructions for obtaining Reddit API authorization data.
