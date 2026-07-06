"""Dedup-store tests against a temporary SQLite file."""
import pytest

import published_store


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISHED_DB", str(tmp_path / "published.sqlite"))
    connection = published_store.open_store()
    yield connection
    connection.close()


def test_env_path_is_used(tmp_path, monkeypatch):
    db_path = tmp_path / "nested" / "published.sqlite"
    monkeypatch.setenv("PUBLISHED_DB", str(db_path))
    assert published_store.store_path() == db_path.resolve()
    connection = published_store.open_store()  # creates parent dirs + schema
    connection.close()
    assert db_path.exists()


def test_unknown_post_is_not_published(store):
    assert published_store.is_published(store, "1abc23") is False


def test_mark_then_is_published(store):
    published_store.mark_published(
        store, "1abc23", "ProgrammerHumor", "Tabs & spaces",
        "https://reddit.com/r/ProgrammerHumor/comments/1abc23/", 4242)
    assert published_store.is_published(store, "1abc23") is True
    # other ids stay unpublished
    assert published_store.is_published(store, "1def45") is False


def test_message_id_round_trip(store):
    published_store.mark_published(
        store, "1def45", "linuxmemes", "It works on my machine",
        "https://reddit.com/r/linuxmemes/comments/1def45/", 777)
    row = store.execute(
        "SELECT subreddit, title, permalink, telegram_message_id "
        "FROM published WHERE reddit_id = ?", ("1def45",)).fetchone()
    assert row == (
        "linuxmemes", "It works on my machine",
        "https://reddit.com/r/linuxmemes/comments/1def45/", 777)


def test_remark_replaces_existing_row(store):
    published_store.mark_published(
        store, "1ghi78", "funnyAnimals", "Saga", "https://p/1", 1)
    published_store.mark_published(
        store, "1ghi78", "funnyAnimals", "Saga", "https://p/1", 2)
    rows = store.execute(
        "SELECT telegram_message_id FROM published WHERE reddit_id = ?",
        ("1ghi78",)).fetchall()
    assert rows == [(2,)]  # INSERT OR REPLACE keeps a single row


def test_dedup_survives_reopen(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISHED_DB", str(tmp_path / "published.sqlite"))
    first = published_store.open_store()
    published_store.mark_published(
        first, "1jkl90", "ProgrammerHumor", "Confession", "https://p/2", 99)
    first.close()
    second = published_store.open_store()
    try:
        assert published_store.is_published(second, "1jkl90") is True
    finally:
        second.close()
