"""Parser tests for trend_watcher against saved Atom / old.reddit HTML fixtures."""
import pytest

import trend_watcher

from conftest import FakeResponse


class TestParseFeed:

    @pytest.fixture
    def candidates(self, rising_atom_bytes):
        return trend_watcher.parse_feed("ProgrammerHumor", rising_atom_bytes)

    def test_entry_order_and_titles(self, candidates):
        assert [candidate["title"] for candidate in candidates] == [
            "Tabs & spaces: the eternal war",
            "It works on my machine",
            "My debugging journey, a saga",
            "Text only confession",
        ]

    def test_reddit_ids_extracted_from_permalinks(self, candidates):
        assert [candidate["reddit_id"] for candidate in candidates] == [
            "1abc23", "1def45", "1ghi78", "1jkl90",
        ]

    def test_permalinks_rewritten_to_reddit_com(self, candidates):
        assert candidates[0]["permalink"] == (
            "https://reddit.com/r/ProgrammerHumor/comments/1abc23/"
            "tabs_spaces_the_eternal_war/"
        )
        for candidate in candidates:
            assert "old.reddit.com" not in candidate["permalink"]

    def test_authors_and_subreddit(self, candidates):
        assert candidates[0]["author"] == "/u/alice"
        assert all(candidate["subreddit"] == "ProgrammerHumor"
                   for candidate in candidates)

    def test_direct_iredd_image_used_verbatim(self, candidates):
        assert candidates[0]["image_url"] == "https://i.redd.it/abcdef123.jpeg"

    def test_preview_thumbnail_upgraded_to_iredd(self, candidates):
        # content only carries preview.redd.it; the parser must upgrade it to
        # the full-resolution i.redd.it original, without the query string.
        assert candidates[1]["image_url"] == "https://i.redd.it/def456gh.png"

    def test_gallery_flag_and_media_thumbnail_fallback(self, candidates):
        gallery = candidates[2]
        assert gallery["is_gallery"] is True
        # image comes from the media:thumbnail element, upgraded off preview
        assert gallery["image_url"] == "https://i.redd.it/ghijk890.jpg"
        # the non-gallery entries must not be flagged
        assert [candidate["is_gallery"] for candidate in candidates] == [
            False, False, True, False,
        ]

    def test_text_post_has_no_image(self, candidates):
        assert candidates[3]["image_url"] is None


class TestRisingScores:

    def test_scores_parsed_from_html(self, monkeypatch, rising_html_text):
        def fake_get(url, headers=None, timeout=None):
            assert url == "https://old.reddit.com/r/ProgrammerHumor/rising/"
            return FakeResponse(rising_html_text)

        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        scores = trend_watcher.rising_scores("ProgrammerHumor")
        assert scores == {
            "1abc23": 1543,
            "1def45": 780,
            "1ghi78": 412,
            "1mno12": -3,  # negative data-score parses
            # promoted thing t3_1pqr34 has no data-score -> excluded
        }

    def test_non_200_yields_empty_mapping(self, monkeypatch):
        def fake_get(url, headers=None, timeout=None):
            return FakeResponse("Forbidden", status_code=403)

        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        assert trend_watcher.rising_scores("ProgrammerHumor") == {}


class TestGalleryImageUrls:

    def test_tiles_enumerated_in_order_with_extensions(
            self, monkeypatch, gallery_html_text):
        requested = []

        def fake_get(url, headers=None, timeout=None):
            requested.append(url)
            return FakeResponse(gallery_html_text)

        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        urls = trend_watcher.gallery_image_urls(
            "https://reddit.com/r/ProgrammerHumor/comments/1ghi78/"
            "my_debugging_journey_a_saga/",
            "1ghi78",
        )
        assert urls == [
            "https://i.redd.it/ghijk890.jpg",   # extension found on page
            "https://i.redd.it/lmnop123.png",   # per-image extension respected
            "https://i.redd.it/noext999.jpg",   # no extension hint -> jpg
        ]
        # duplicated lightbox tile deduped, other post's tile (9zzz99) ignored
        assert len(urls) == 3
        # the fetch goes through old.reddit
        assert requested == [
            "https://old.reddit.com/r/ProgrammerHumor/comments/1ghi78/"
            "my_debugging_journey_a_saga/",
        ]

    def test_unreachable_page_yields_empty_list(self, monkeypatch):
        def fake_get(url, headers=None, timeout=None):
            return FakeResponse("gone", status_code=404)

        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        assert trend_watcher.gallery_image_urls(
            "https://reddit.com/r/x/comments/abc/x/", "abc") == []


class TestListingUrls:

    def test_rising_maps_to_plain_paths(self):
        rss_url, html_url = trend_watcher.listing_urls("ProgrammerHumor", "rising")
        assert rss_url == "https://old.reddit.com/r/ProgrammerHumor/rising.rss"
        assert html_url == "https://old.reddit.com/r/ProgrammerHumor/rising/"

    def test_top_week_maps_to_t_query(self):
        rss_url, html_url = trend_watcher.listing_urls("linuxmemes", "top:week")
        assert rss_url == "https://old.reddit.com/r/linuxmemes/top.rss?t=week"
        assert html_url == "https://old.reddit.com/r/linuxmemes/top/?t=week"

    def test_spec_whitespace_tolerated(self):
        rss_url, html_url = trend_watcher.listing_urls("funnyAnimals", " top : month ")
        assert rss_url == "https://old.reddit.com/r/funnyAnimals/top.rss?t=month"
        assert html_url == "https://old.reddit.com/r/funnyAnimals/top/?t=month"


class TestFetchListing:

    def test_fetch_listing_requests_listing_rss(self, monkeypatch, rising_atom_bytes):
        requested = []

        def fake_get(url, headers=None, timeout=None):
            requested.append(url)
            return FakeResponse(rising_atom_bytes)

        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        candidates = trend_watcher.fetch_listing("ProgrammerHumor", "top:week")
        assert requested == [
            "https://old.reddit.com/r/ProgrammerHumor/top.rss?t=week"]
        assert len(candidates) == 4

    def test_listing_scores_requests_listing_html(self, monkeypatch, rising_html_text):
        requested = []

        def fake_get(url, headers=None, timeout=None):
            requested.append(url)
            return FakeResponse(rising_html_text)

        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        scores = trend_watcher.listing_scores("ProgrammerHumor", "top:week")
        assert requested == [
            "https://old.reddit.com/r/ProgrammerHumor/top/?t=week"]
        assert scores  # fixture yields a non-empty score map
