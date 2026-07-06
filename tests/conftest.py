"""Shared test setup: make the flat app/ modules importable and load fixtures.

The publisher modules import each other by bare name (``import trend_watcher``),
so tests put app/ itself on sys.path instead of importing through a package.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class FakeResponse:
    """Stand-in for requests.Response: canned status, text, and content."""

    def __init__(self, body, status_code=200):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else body.decode("utf-8")
        self.content = body if isinstance(body, bytes) else body.encode("utf-8")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        raise RuntimeError("no JSON in fixture responses")


def fixture_text(name):
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def fixture_bytes(name):
    return (FIXTURES_DIR / name).read_bytes()


@pytest.fixture
def rising_atom_bytes():
    return fixture_bytes("rising.atom.xml")


@pytest.fixture
def rising_html_text():
    return fixture_text("rising.html")


@pytest.fixture
def gallery_html_text():
    return fixture_text("gallery.html")


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    """Fail loudly if any test reaches for the real network.

    Tests that need HTTP re-monkeypatch requests.get / requests.post on the
    module under test after this fixture has run.
    """
    def refuse(*args, **kwargs):
        raise AssertionError(f"network access attempted: {args} {kwargs}")

    monkeypatch.setattr("requests.sessions.Session.request", refuse)
