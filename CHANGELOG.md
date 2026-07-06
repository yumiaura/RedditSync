# Changelog

## Unreleased

### Added
- Trend auto-publisher (`feat/trend-publisher`): fetches rising posts for each
  subreddit in `TREND_SUBREDDITS` via public Atom feeds (no OAuth needed),
  picks the best not-yet-published post that has an image, and sends
  photo + caption (title + `r/<subreddit>` link) to a Telegram channel.
  - `app/trend_watcher.py` — RSS rising reader with rate-limit backoff.
  - `app/telegram_publisher.py` — Telegram photo posting with upload fallback.
  - `app/published_store.py` — SQLite store of published Reddit post ids for
    deduplication (records the Telegram `message_id` of each post).
  - `app/publish_trends.py` — orchestrator; one post per tracked subreddit per
    run, so two subreddits on a twice-daily schedule means four posts per day.
  - `app/trend_scheduler.py` — APScheduler cron runner driven by `PUBLISH_TIMES`
    (default `09:00,21:00` UTC).
  - `tools/backfill_published.py` — records an already-posted meme so it is
    never reposted.
- Docker packaging (`feat/trend-publisher`): `Dockerfile` and `docker-compose.yml`
  to run the scheduler unattended with a mounted dedup store.
- New environment variables documented in `env.example`: `TELEGRAM_TOKEN`,
  `TELEGRAM_CHANNEL_ID`, `TREND_SUBREDDITS`, `PUBLISH_TIMES`, `PUBLISHED_DB`.
- `.dockerignore` to keep the image small (excludes `.git`, caches, media,
  local databases).

### Changed
- `README.md` rewritten: a banner at the top links the live Telegram channel
  ([t.me/humorfromyumi](https://t.me/humorfromyumi)) and the trend publisher is
  documented as a first-class feature alongside the sync engine.
- `tools/backfill_published.py` now loads `.env` so it writes to the same
  `PUBLISHED_DB` the publisher reads.
