"""Selection/threshold tests for publish_trends.pick_unsent and env parsing."""
import pytest

import publish_trends
import published_store


def make_candidate(reddit_id, title="A meme", image_url="https://i.redd.it/x.jpg",
                   is_gallery=False, score=900, images=None):
    if images is None:
        images = [image_url] if image_url else []
    return {
        "subreddit": "ProgrammerHumor",
        "reddit_id": reddit_id,
        "title": title,
        "author": "/u/someone",
        "permalink": f"https://reddit.com/r/ProgrammerHumor/comments/{reddit_id}/",
        "score": score,
        "image_url": image_url,
        "images": images,
        "is_gallery": is_gallery,
    }


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISHED_DB", str(tmp_path / "published.sqlite"))
    connection = published_store.open_store()
    yield connection
    connection.close()


def test_first_eligible_candidate_wins(store):
    candidates = [make_candidate("1abc23", score=900),
                  make_candidate("1def45", score=1200)]
    choice = publish_trends.pick_unsent(store, candidates, 500)
    # listing order decides, not the higher score further down
    assert choice["reddit_id"] == "1abc23"


def test_below_threshold_is_skipped(store):
    candidates = [make_candidate("1abc23", score=499),
                  make_candidate("1def45", score=500)]
    choice = publish_trends.pick_unsent(store, candidates, 500)
    assert choice["reddit_id"] == "1def45"  # threshold is inclusive (>=)


def test_missing_score_counts_as_zero(store):
    candidate = make_candidate("1abc23")
    del candidate["score"]
    assert publish_trends.pick_unsent(store, [candidate], 500) is None


def test_already_published_is_skipped(store):
    published_store.mark_published(
        store, "1abc23", "ProgrammerHumor", "A meme",
        "https://reddit.com/r/ProgrammerHumor/comments/1abc23/", 111)
    candidates = [make_candidate("1abc23"), make_candidate("1def45", score=800)]
    choice = publish_trends.pick_unsent(store, candidates, 500)
    assert choice["reddit_id"] == "1def45"


def test_candidate_without_image_is_skipped(store):
    candidates = [make_candidate("1abc23", image_url=None),
                  make_candidate("1def45", score=800)]
    choice = publish_trends.pick_unsent(store, candidates, 500)
    assert choice["reddit_id"] == "1def45"


def test_candidate_without_reddit_id_is_skipped(store):
    candidates = [make_candidate(None), make_candidate("1def45", score=800)]
    choice = publish_trends.pick_unsent(store, candidates, 500)
    assert choice["reddit_id"] == "1def45"


def test_no_eligible_candidate_returns_none(store):
    candidates = [make_candidate("1abc23", image_url=None),
                  make_candidate("1def45", score=10)]
    assert publish_trends.pick_unsent(store, candidates, 500) is None


def test_min_score_env_override(monkeypatch):
    monkeypatch.setenv("MIN_SCORE", "750")
    assert publish_trends.min_score() == 750


def test_min_score_default(monkeypatch):
    monkeypatch.delenv("MIN_SCORE", raising=False)
    assert publish_trends.min_score() == publish_trends.DEFAULT_MIN_SCORE == 500


def test_tracked_subreddits_parsing(monkeypatch):
    monkeypatch.setenv("TREND_SUBREDDITS",
                       " ProgrammerHumor , funnyAnimals ,, linuxmemes ")
    assert publish_trends.tracked_subreddits() == [
        "ProgrammerHumor", "funnyAnimals", "linuxmemes"]


def test_listing_chain_default(monkeypatch):
    monkeypatch.delenv("TREND_LISTINGS", raising=False)
    assert publish_trends.listing_chain() == ["rising", "top:week"]


def test_listing_chain_env_override(monkeypatch):
    monkeypatch.setenv("TREND_LISTINGS", " rising ,, top:month ")
    assert publish_trends.listing_chain() == ["rising", "top:month"]


@pytest.fixture
def listing_stubs(monkeypatch):
    """Stub trend_watcher per listing and record which listings were fetched."""
    import trend_watcher

    fetched = []
    feeds = {}
    failures = set()

    def fake_fetch_listing(subreddit, listing="rising", retries=4, pause=35):
        fetched.append(listing)
        if listing in failures:
            raise RuntimeError("HTTP 401")
        return feeds.get(listing, [])

    monkeypatch.setattr(trend_watcher, "fetch_listing", fake_fetch_listing)
    monkeypatch.setattr(publish_trends.time, "sleep", lambda seconds: None)
    return {"fetched": fetched, "feeds": feeds, "failures": failures}


def test_select_candidate_falls_back_to_top_week(store, listing_stubs):
    listing_stubs["feeds"]["rising"] = [make_candidate("1low01", score=42)]
    listing_stubs["feeds"]["top:week"] = [make_candidate("1top99", score=4200)]

    choice = publish_trends.select_candidate(store, "ProgrammerHumor", 500)

    assert choice["reddit_id"] == "1top99"
    assert choice["score"] == 4200
    assert listing_stubs["fetched"] == ["rising", "top:week"]


def test_select_candidate_skips_fallback_when_rising_delivers(store, listing_stubs):
    listing_stubs["feeds"]["rising"] = [make_candidate("1hot42", score=900)]
    listing_stubs["feeds"]["top:week"] = [make_candidate("1top99", score=4200)]

    choice = publish_trends.select_candidate(store, "ProgrammerHumor", 500)

    assert choice["reddit_id"] == "1hot42"
    assert listing_stubs["fetched"] == ["rising"]  # no needless second request


def test_select_candidate_exhausted_chain_returns_none(store, listing_stubs):
    listing_stubs["feeds"]["rising"] = [make_candidate("1low01", score=42)]
    listing_stubs["feeds"]["top:week"] = []

    assert publish_trends.select_candidate(store, "ProgrammerHumor", 500) is None
    assert listing_stubs["fetched"] == ["rising", "top:week"]


def test_select_candidate_survives_a_failing_listing(store, listing_stubs):
    listing_stubs["failures"].add("rising")
    listing_stubs["feeds"]["top:week"] = [make_candidate("1top99", score=4200)]

    choice = publish_trends.select_candidate(store, "ProgrammerHumor", 500)

    assert choice["reddit_id"] == "1top99"
    assert listing_stubs["fetched"] == ["rising", "top:week"]


def test_select_candidate_skips_published_in_fallback(store, listing_stubs):
    published_store.mark_published(
        store, "1top99", "ProgrammerHumor", "A meme",
        "https://reddit.com/r/ProgrammerHumor/comments/1top99/", 111)
    listing_stubs["feeds"]["rising"] = []
    listing_stubs["feeds"]["top:week"] = [make_candidate("1top99", score=4200),
                                          make_candidate("1new77", score=800)]

    choice = publish_trends.select_candidate(store, "ProgrammerHumor", 500)

    assert choice["reddit_id"] == "1new77"


def test_publish_once_limits_to_given_subreddits(monkeypatch, tmp_path):
    monkeypatch.setenv("PUBLISHED_DB", str(tmp_path / "published.sqlite"))
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "-100")
    monkeypatch.setenv("TREND_SUBREDDITS", "ProgrammerHumor,funnyAnimals,linuxmemes")
    asked = []

    def fake_select(connection, subreddit, threshold):
        asked.append(subreddit)
        return None

    monkeypatch.setattr(publish_trends, "select_candidate", fake_select)
    publish_trends.publish_once(dry_run=True, subreddits=["funnyAnimals"])
    assert asked == ["funnyAnimals"]


def test_publish_once_defaults_to_tracked_subreddits(monkeypatch, tmp_path):
    monkeypatch.setenv("PUBLISHED_DB", str(tmp_path / "published.sqlite"))
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "-100")
    monkeypatch.setenv("TREND_SUBREDDITS", "a,b")
    asked = []

    def fake_select(connection, subreddit, threshold):
        asked.append(subreddit)
        return None

    monkeypatch.setattr(publish_trends, "select_candidate", fake_select)
    monkeypatch.setattr(publish_trends.time, "sleep", lambda seconds: None)
    publish_trends.publish_once(dry_run=True)
    assert asked == ["a", "b"]
