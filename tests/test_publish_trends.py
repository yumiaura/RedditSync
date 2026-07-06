"""Selection/threshold tests for publish_trends.pick_unsent and env parsing."""
import pytest

import publish_trends
import published_store


def make_candidate(reddit_id, title="A meme", image_url="https://i.redd.it/x.jpg",
                   is_gallery=False):
    return {
        "subreddit": "ProgrammerHumor",
        "reddit_id": reddit_id,
        "title": title,
        "author": "/u/someone",
        "permalink": f"https://reddit.com/r/ProgrammerHumor/comments/{reddit_id}/",
        "image_url": image_url,
        "is_gallery": is_gallery,
    }


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISHED_DB", str(tmp_path / "published.sqlite"))
    connection = published_store.open_store()
    yield connection
    connection.close()


def test_first_eligible_candidate_wins(store):
    candidates = [make_candidate("1abc23"), make_candidate("1def45")]
    scores = {"1abc23": 900, "1def45": 1200}
    choice = publish_trends.pick_unsent(store, candidates, scores, 500)
    # feed order decides, not the higher score further down
    assert choice["reddit_id"] == "1abc23"


def test_below_threshold_is_skipped(store):
    candidates = [make_candidate("1abc23"), make_candidate("1def45")]
    scores = {"1abc23": 499, "1def45": 500}
    choice = publish_trends.pick_unsent(store, candidates, scores, 500)
    assert choice["reddit_id"] == "1def45"  # threshold is inclusive (>=)


def test_missing_score_counts_as_zero(store):
    candidates = [make_candidate("1abc23")]
    choice = publish_trends.pick_unsent(store, candidates, {}, 500)
    assert choice is None


def test_already_published_is_skipped(store):
    published_store.mark_published(
        store, "1abc23", "ProgrammerHumor", "A meme",
        "https://reddit.com/r/ProgrammerHumor/comments/1abc23/", 111)
    candidates = [make_candidate("1abc23"), make_candidate("1def45")]
    scores = {"1abc23": 900, "1def45": 800}
    choice = publish_trends.pick_unsent(store, candidates, scores, 500)
    assert choice["reddit_id"] == "1def45"


def test_candidate_without_image_is_skipped(store):
    candidates = [make_candidate("1abc23", image_url=None),
                  make_candidate("1def45")]
    scores = {"1abc23": 900, "1def45": 800}
    choice = publish_trends.pick_unsent(store, candidates, scores, 500)
    assert choice["reddit_id"] == "1def45"


def test_candidate_without_reddit_id_is_skipped(store):
    candidates = [make_candidate(None), make_candidate("1def45")]
    scores = {"1def45": 800}
    choice = publish_trends.pick_unsent(store, candidates, scores, 500)
    assert choice["reddit_id"] == "1def45"


def test_no_eligible_candidate_returns_none(store):
    candidates = [make_candidate("1abc23", image_url=None),
                  make_candidate("1def45")]
    scores = {"1def45": 10}
    assert publish_trends.pick_unsent(store, candidates, scores, 500) is None


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
