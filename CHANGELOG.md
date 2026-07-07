# Changelog

## Unreleased

### Added
- `.github/FUNDING.yml` with GitHub Sponsors, Buy Me a Coffee and Patreon links
  (`chore/funding`).
- Configurable publish timezone: `PUBLISH_TIMES` slots are now interpreted in
  the `PUBLISH_TZ` IANA timezone (default `UTC`, e.g. `Europe/Lisbon`).
  An invalid name fails at startup with a clear error instead of silently
  scheduling in the wrong timezone (`feat/publish-timezone`).
- Staggered publishing: within each `PUBLISH_TIMES` slot the tracked
  subreddits now post `PUBLISH_INTERVAL` minutes apart (default 60) via one
  cron job per (slot, subreddit), so the channel gets roughly one post per
  hour instead of a burst of three. Restart-safe — no long sleeps inside a
  job (`feat/staggered-publish`).

### Fixed (deployment)
- The container user's uid is now the `APP_UID` build argument (set it in
  `.env` to `id -u`, default 1000) instead of hardcoded 1000. On hosts where
  the user is not uid 1000 the publisher could send a Telegram post and then
  crash with "attempt to write a readonly database" before recording it in
  the dedup store — a repost risk (`fix/container-uid`).

### Changed
- Default `MIN_SCORE` lowered from 1000 to 500 (`chore/min-score-500`). It is a
  per-post threshold (each published post needs at least this many upvotes), not
  a total across posts; rising posts rarely reach 1000 so 1000 left channels
  like r/funnyAnimals with nothing to publish.
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
- Captions no longer carry a decorative leading emoji — just the bold title and
  the `r/<subreddit>` link.
- `README.md` rewritten: a banner at the top links the live Telegram channel
  ([t.me/humorfromyumi](https://t.me/humorfromyumi)) and the trend publisher is
  documented as a first-class feature alongside the sync engine.
- `tools/backfill_published.py` now loads `.env` so it writes to the same
  `PUBLISHED_DB` the publisher reads.
- `trend_watcher.extract_image` now returns full-resolution images: it upgrades
  140px `preview.redd.it` thumbnails (e.g. gallery posts) to the original
  `i.redd.it` file and skips posts with no full-size image, so the channel never
  shows a tiny thumbnail.
- `PUBLISHED_DB` relative paths resolve against the repo root, so the publisher,
  scheduler and tools share one dedup store regardless of working directory.
- Default `TREND_SUBREDDITS` in `env.example` now includes `linuxmemes`.

### Added (continued)
- Score threshold: only posts with a score of at least `MIN_SCORE` (default
  1000) are published. Scores are read from the old.reddit rising HTML
  (`data-score`), since the Atom feed carries none — `trend_watcher.rising_scores`.
- Gallery posts are published as a single Telegram **album** (`sendMediaGroup`)
  instead of one image. Gallery images are enumerated from the old.reddit HTML
  (`id="media-tile-<post>-<media>"`, reachable without OAuth) and upgraded to
  full-resolution `i.redd.it` URLs. `app/telegram_publisher.py` gains
  `send_media_group`; `app/trend_watcher.py` gains `gallery_image_urls`.

### Security
- Web UI: `/media/<path>` now resolves the requested file and refuses anything
  outside `media/`, closing a path traversal where `../../etc/...` could be
  read through the HTML/PDF/image fallbacks (`fix/security-hardening`).
- Web UI: the Flask debug server (Werkzeug interactive debugger — remote code
  execution if reachable) is gated behind `FLASK_DEBUG`, default off; README
  documents running behind a real WSGI server (`fix/security-hardening`).
- Media downloader: downloads are restricted to http(s) URLs on a Reddit/imgur
  host allowlist, enforced via an httpx request hook on the initial URL, every
  redirect hop (now capped at 5) and any URL scraped from `og:image` metadata —
  closing the SSRF where a redirect or crafted HTML page could make the
  downloader fetch arbitrary URLs (`fix/security-hardening`).
- Media downloader: `max_size` is now enforced while streaming to disk, so a
  response without a `Content-Length` header can no longer grow unbounded; an
  aborted download removes its partial file (`fix/security-hardening`).

### Fixed
- Media downloader: the re-read path after sniffing an HTML preview called
  `Response.aread()` with a size argument (not supported) and reassigned
  `client.stream(...)` — a context manager, not a response — so it raised at
  runtime; the preview is now read via `aiter_bytes` and the body re-requested
  with a fresh stream (`fix/security-hardening`).
- One database layer instead of two: the unused `DatabaseManager` class is
  deleted and `main.py`/`sync_worker.py` now share the module-level engine the
  web UI already used, so media sync no longer depends on globals that
  `main.py` never initialized (`fix/security-hardening`).
- One database path everywhere: every entry point now derives it from the
  env-driven `DB_PATH` (default `./news.db`, resolved against the repo root
  like `PUBLISHED_DB`); the web UI previously opened a hardcoded — and
  nonexistent — `db.sqlite` and showed an empty site. `MEDIA_DIR` resolves the
  same way, so the engine and the web UI share one media folder regardless of
  the working directory (`fix/security-hardening`).
- Media download re-enabled: `sync_all` calls `sync_pending_media` again
  instead of carrying it commented out, so the advertised "Media Download"
  feature actually runs (`fix/security-hardening`).

### Changed (continued)
- Underscore-prefixed identifiers renamed to public names per project
  convention: `_engine`/`_session_factory` → `engine`/`session_factory`
  (`app/db.py`), `_db_initialized` → `db_initialized` (`web/app.py`)
  (`fix/security-hardening`).
- Fresh databases are no longer seeded with a hardcoded `r/unixporn`
  subscription; seeds come from the optional comma-separated
  `DEFAULT_SUBSCRIPTIONS` env variable and default to none
  (`fix/security-hardening`).
- `requirements.txt`: every dependency pinned to the exact version the test
  harnesses run against; the empty `# scheduler` stub removed
  (`fix/security-hardening`).

### Added (hygiene)
- `LICENSE` file (MIT), matching the claim in the README
  (`fix/security-hardening`).

### Changed (code quality)
- Error handling pass across `app/` and `web/`: `print()` calls replaced with
  `logging`; broad `except Exception` blocks either narrowed to the expected
  exceptions (`media_downloader.download_media`,
  `reddit_client.extract_media_url`, the web image fallback) or switched to
  `logger.exception` so tracebacks are preserved; the downloader retry now
  re-raises the original error instead of a wrapped `RetryError`
  (`fix/security-hardening`).
- `web/app.py`: repeated in-function `from sqlalchemy import select` imports
  hoisted to module top; unused imports removed repo-wide (ruff F401 clean)
  (`fix/security-hardening`).
- `trend_watcher` logs a warning whenever a rising feed, the rising HTML
  scores or a gallery page parse to zero results, so an old.reddit markup
  change is visible in the logs instead of silently publishing nothing
  (`fix/security-hardening`).
- `trend_scheduler` shuts down gracefully on SIGTERM (clean `docker stop`),
  optionally writes a rotating log file (`LOG_FILE`, 5 MB × 3 backups) and
  refreshes a heartbeat file (`HEARTBEAT_FILE`) every minute
  (`fix/security-hardening`).
- Dockerfile: the container now runs as a non-root `appuser` (uid 1000, so
  the mounted `./data` volume stays writable) and gains a `HEALTHCHECK` that
  flags the container unhealthy when the scheduler heartbeat goes stale
  (`fix/security-hardening`).

### Added (publisher)
- Configurable listing chain with `top?t=week` fallback: the publisher walks
  `TREND_LISTINGS` (default `rising,top:week`) per subreddit and publishes
  from the first listing that yields an unposted image post above `MIN_SCORE`,
  so a slow subreddit gets the week's best post instead of silence.
  `trend_watcher` gains `listing_urls`/`fetch_listing`/`listing_scores`
  (with `fetch_rising`/`rising_scores` kept as thin wrappers) and a shared
  `get_with_backoff` helper; `publish_trends` gains `listing_chain` and
  `select_candidate` (`fix/security-hardening`).

### Added (tests & CI)
- Offline pytest suite (32 tests, ~2 s): `trend_watcher` parsers against
  saved Atom/HTML fixtures (including the preview→i.redd.it upgrade, gallery
  enumeration and score scraping), `published_store` dedup and persistence,
  `telegram_publisher.build_caption` layout/escaping, and
  `publish_trends.pick_unsent` threshold/selection logic. An autouse fixture
  blocks accidental real network calls (`fix/security-hardening`).
- `requirements-dev.txt` (pytest, ruff) and `pytest.ini`
  (`fix/security-hardening`).
- GitHub Actions workflow running `ruff check` and `pytest` on every push to
  `main` and every pull request (`fix/security-hardening`).
- README gains a Tests section (`fix/security-hardening`).

### Removed
- `news.sql` — a raw-SQL dump left over from before the ORM migration,
  referenced by nothing in the repo (`fix/security-hardening`).
