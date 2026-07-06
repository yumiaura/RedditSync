# Roadmap

Improvement backlog from a code review on 2026-07-05, ordered by priority.
Each item notes the file and why it matters. Check items off as they land.

## 🔴 Security — fix before the repo goes public or the web UI is exposed

- [ ] **Path traversal in media serving.** `web/app.py` `media_file()` joins the
      user-supplied `<path:filename>` onto `MEDIA_DIR` and then `open()`s /
      `send_file()`s the result. The image branch uses the safe
      `send_from_directory`, but the HTML and image-preview fallbacks read the
      raw joined path, so `../../etc/...` can read files outside `media/`.
      Resolve the path and assert it stays under `MEDIA_DIR`
      (`Path(p).resolve().is_relative_to(MEDIA_DIR)`), or serve everything
      through `send_from_directory`.
- [ ] **Flask debug server.** `web/app.py` ends with `app.run(debug=True)`,
      which enables the Werkzeug interactive debugger (remote code execution if
      reachable). Gate debug behind an env flag, default off, and document
      running behind a real WSGI server.
- [ ] **Download size trusts the `Content-Length` header.** `app/media_downloader.py`
      only checks `content-length`; a response without it streams to disk
      unbounded. Count bytes while streaming and abort past `max_size`.
- [ ] **SSRF via redirects and scraped `og:image`.** `app/media_downloader.py`
      follows redirects and re-downloads an arbitrary `content="..."` URL pulled
      from HTML. Restrict schemes/hosts to a Reddit/imgur allowlist before
      fetching.

## 🟠 Correctness / bugs

- [ ] **Media download is silently disabled.** `app/sync_worker.py` has
      `# await sync_pending_media(...)` commented out, so the advertised
      "Media Download" feature never runs. Re-enable it or drop the claim.
- [ ] **Two parallel DB layers that don't share state.** `app/db.py` defines
      both a `DatabaseManager` class and module-level globals
      (`init_db`/`get_session` over a global engine). `main.py` uses the class;
      `sync_worker.sync_media_item` and `web/app.py` use the globals, which stay
      uninitialized under `main.py` and raise `RuntimeError` if media sync is
      re-enabled. Keep one layer, delete the other.
- [ ] **Inconsistent database path.** Default is `db.sqlite` in `app/config.py`
      and `app/db.py`, `./news.db` in `env.example`, and hardcoded `db.sqlite`
      in `web/app.py`, while the committed database is `news.db`. The web UI can
      open a different/empty database than the sync engine. Unify on one
      env-driven path.
- [ ] **Broken stream re-open in the downloader.** `app/media_downloader.py`
      reassigns `response = await client.stream(...)` (a context manager, not a
      response) after reading the preview; iterating it will fail. Fix the
      re-read path.

## 🟡 Public-repo hygiene — things that read as unfinished

- [ ] **No LICENSE file.** README claims MIT "see the LICENSE file", but none
      exists. Add `LICENSE` or correct the claim.
- [ ] **README references missing files.** Quick Start calls
      `tools/migrate_add_metrics.py` and `tools/test_scheduler.py`; neither
      exists. Remove or add them.
- [ ] **"Running Tests" section with no tests.** README documents `pytest` and
      `requirements-dev.txt`, but there is no test suite and no dev
      requirements file. Add tests (below) or drop the section.
- [ ] **Hardcoded personal default subscription.** `app/db.py` seeds
      `r/unixporn` into every fresh database. Make the seed configurable or
      empty by default.
- [ ] **Unpinned dependencies.** `requirements.txt` has no versions (except
      `sqlalchemy>=2.0.0`) and an empty `# scheduler` stub. Pin versions and
      remove the stub.
- [ ] **Legacy `news.sql`.** Raw-SQL dump left from before the ORM migration —
      remove if unused (confirm first).
- [ ] **Placeholder clone URL.** README uses `.../yourusername/RedditSync.git`;
      point it at `yumiaura/RedditSync`.

## 🟢 Code quality

- [ ] **Underscore-prefixed identifiers.** `_engine`, `_session_factory`
      (`app/db.py`), `_db_initialized` (`web/app.py`) break the project's
      no-single-underscore rule. Rename to public names.
- [ ] **Broad `except Exception`.** Across `app/main.py`, `sync_worker.py`,
      `reddit_client.py`, `media_downloader.py`, `web/app.py` — narrow to the
      expected exceptions, or `logger.exception` and re-raise where the caller
      should know.
- [ ] **`print()` for errors in the web app.** `web/app.py` prints PDF/DB
      errors; use `logging`.
- [ ] **Imports inside functions.** `from sqlalchemy import select` and
      `from .models import ...` are repeated inside `web/app.py` and
      `sync_worker.py`; hoist to module top.
- [ ] **Fragile HTML scraping.** `app/trend_watcher.py` (`rising_scores`,
      `gallery_image_urls`) depends on old.reddit markup. Log a warning when a
      page yields zero results so breakage is visible instead of silent.

## 🔵 Tests & CI

- [ ] Add a `pytest` suite: `trend_watcher` parsers against saved HTML/RSS
      fixtures, `published_store` dedup, `telegram_publisher.build_caption`, and
      `publish_trends.pick_unsent` threshold logic.
- [ ] Add `requirements-dev.txt` (pytest, a linter such as ruff).
- [ ] Add a GitHub Actions workflow running lint + tests on push and PR.

## ⚪ Nice to have

- [ ] Fallback to `top?t=week` when a subreddit's rising has nothing above
      `MIN_SCORE` (confirmed reachable via old.reddit HTML) — a configurable
      listing chain.
- [ ] Dockerfile: run as a non-root `USER` and add a `HEALTHCHECK`.
- [ ] Graceful shutdown for `trend_scheduler` (handle SIGTERM so `docker stop`
      is clean).
- [ ] Rotating file logs for the publisher when run outside Docker.
