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
