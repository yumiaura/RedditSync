"""Timezone handling tests for trend_scheduler."""
from zoneinfo import ZoneInfo

import pytest

import trend_scheduler


def test_default_timezone_is_utc(monkeypatch):
    monkeypatch.delenv("PUBLISH_TZ", raising=False)
    assert trend_scheduler.publish_timezone() == ZoneInfo("UTC")


def test_env_timezone_override(monkeypatch):
    monkeypatch.setenv("PUBLISH_TZ", " Europe/Lisbon ")
    assert trend_scheduler.publish_timezone() == ZoneInfo("Europe/Lisbon")


def test_empty_env_falls_back_to_utc(monkeypatch):
    monkeypatch.setenv("PUBLISH_TZ", "")
    assert trend_scheduler.publish_timezone() == ZoneInfo("UTC")


def test_invalid_timezone_fails_loudly(monkeypatch):
    monkeypatch.setenv("PUBLISH_TZ", "Europe/Lisboa")
    with pytest.raises(Exception):
        trend_scheduler.publish_timezone()


def test_staggered_schedule_default_layout():
    schedule = trend_scheduler.staggered_schedule(
        ["09:00", "21:00"], ["ProgrammerHumor", "funnyAnimals", "linuxmemes"], 60)
    assert schedule == [
        (9, 0, "ProgrammerHumor"),
        (10, 0, "funnyAnimals"),
        (11, 0, "linuxmemes"),
        (21, 0, "ProgrammerHumor"),
        (22, 0, "funnyAnimals"),
        (23, 0, "linuxmemes"),
    ]


def test_staggered_schedule_wraps_past_midnight():
    schedule = trend_scheduler.staggered_schedule(["23:30"], ["a", "b"], 60)
    assert schedule == [(23, 30, "a"), (0, 30, "b")]


def test_staggered_schedule_custom_interval():
    schedule = trend_scheduler.staggered_schedule(["09:00"], ["a", "b", "c"], 90)
    assert schedule == [(9, 0, "a"), (10, 30, "b"), (12, 0, "c")]


def test_publish_interval_default(monkeypatch):
    monkeypatch.delenv("PUBLISH_INTERVAL", raising=False)
    assert trend_scheduler.publish_interval_minutes() == 60


def test_publish_interval_env_override(monkeypatch):
    monkeypatch.setenv("PUBLISH_INTERVAL", "45")
    assert trend_scheduler.publish_interval_minutes() == 45
