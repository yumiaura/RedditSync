# Changelog

## Unreleased

### Added
- `.github/FUNDING.yml` with GitHub Sponsors, Buy Me a Coffee and Patreon links
  (`chore/funding`).

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
