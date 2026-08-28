"""Parser and request tests for trend_watcher against a saved API listing."""
import pytest

import trend_watcher

from conftest import FakeResponse


@pytest.fixture(autouse=True)
def oauth_env(monkeypatch):
    """Credentials every API call needs, plus a clean token cache per test."""
    monkeypatch.setenv("REDDIT_CLIENT_ID", "client")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_REFRESH_TOKEN", "refresh")
    monkeypatch.setattr(trend_watcher, "token_cache",
                        {"value": None, "expires_at": 0.0})
    monkeypatch.setattr(trend_watcher.time, "sleep", lambda seconds: None)


def token_response():
    return FakeResponse('{"access_token": "bearer-token", "expires_in": 3600}')


class TestParseListing:

    @pytest.fixture
    def candidates(self, rising_payload):
        return trend_watcher.parse_listing("ProgrammerHumor", rising_payload)

    def test_entry_order_and_titles(self, candidates):
        assert [candidate["title"] for candidate in candidates] == [
            "Tabs & spaces: the eternal war",
            "It works on my machine",
            "My debugging journey, a saga",
            "Text only confession",
        ]

    def test_reddit_ids_taken_from_the_api(self, candidates):
        assert [candidate["reddit_id"] for candidate in candidates] == [
            "1abc23", "1def45", "1ghi78", "1jkl90",
        ]

    def test_permalinks_are_absolute_reddit_com_urls(self, candidates):
        assert candidates[0]["permalink"] == (
            "https://reddit.com/r/ProgrammerHumor/comments/1abc23/"
            "tabs_spaces_the_eternal_war/"
        )
        for candidate in candidates:
            assert candidate["permalink"].startswith("https://reddit.com/")

    def test_authors_and_subreddit(self, candidates):
        assert candidates[0]["author"] == "/u/alice"
        assert all(candidate["subreddit"] == "ProgrammerHumor"
                   for candidate in candidates)

    def test_scores_come_with_the_listing(self, candidates):
        assert [candidate["score"] for candidate in candidates] == [
            1543, 780, 412, -3,
        ]

    def test_direct_iredd_image_used_verbatim(self, candidates):
        assert candidates[0]["image_url"] == "https://i.redd.it/abcdef123.jpeg"
        assert candidates[0]["images"] == ["https://i.redd.it/abcdef123.jpeg"]

    def test_preview_source_upgraded_to_iredd(self, candidates):
        # the post links to its own comments page; the image lives in preview,
        # which must be upgraded to the full-resolution i.redd.it original
        # without the query string.
        assert candidates[1]["image_url"] == "https://i.redd.it/def456gh.png"

    def test_gallery_images_enumerated_in_order(self, candidates):
        gallery = candidates[2]
        assert gallery["is_gallery"] is True
        assert gallery["images"] == [
            "https://i.redd.it/ghijk890.jpg",   # extension from media_metadata
            "https://i.redd.it/lmnop123.png",   # per-image mime respected
            "https://i.redd.it/noext999.jpg",   # no mime -> preview upgraded
        ]
        assert gallery["image_url"] == "https://i.redd.it/ghijk890.jpg"
        assert [candidate["is_gallery"] for candidate in candidates] == [
            False, False, True, False,
        ]

    def test_text_post_has_no_image(self, candidates):
        assert candidates[3]["image_url"] is None
        assert candidates[3]["images"] == []

    def test_empty_listing_yields_no_candidates(self):
        assert trend_watcher.parse_listing("x", {"data": {"children": []}}) == []


class TestListingRequest:

    def test_rising_maps_to_plain_path(self):
        path, params = trend_watcher.listing_request("ProgrammerHumor", "rising")
        assert path == "/r/ProgrammerHumor/rising"
        assert params == {"limit": trend_watcher.LISTING_LIMIT, "raw_json": 1}

    def test_top_week_maps_to_t_parameter(self):
        path, params = trend_watcher.listing_request("linuxmemes", "top:week")
        assert path == "/r/linuxmemes/top"
        assert params["t"] == "week"

    def test_spec_whitespace_tolerated(self):
        path, params = trend_watcher.listing_request("funnyAnimals", " top : month ")
        assert path == "/r/funnyAnimals/top"
        assert params["t"] == "month"


class TestAccessToken:

    def test_token_minted_from_refresh_token_and_cached(self, monkeypatch):
        posts = []

        def fake_post(url, auth=None, data=None, headers=None, timeout=None):
            posts.append((url, auth, data["grant_type"]))
            return token_response()

        monkeypatch.setattr(trend_watcher.requests, "post", fake_post)
        assert trend_watcher.access_token() == "bearer-token"
        assert trend_watcher.access_token() == "bearer-token"  # served from cache
        assert posts == [(trend_watcher.TOKEN_URL, ("client", "secret"),
                          "refresh_token")]

    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.delenv("REDDIT_REFRESH_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="REDDIT_REFRESH_TOKEN"):
            trend_watcher.access_token()

    def test_rejected_refresh_token_raises(self, monkeypatch):
        def fake_post(url, auth=None, data=None, headers=None, timeout=None):
            return FakeResponse('{"error": "invalid_grant"}', status_code=400)

        monkeypatch.setattr(trend_watcher.requests, "post", fake_post)
        with pytest.raises(RuntimeError, match="HTTP 400"):
            trend_watcher.access_token()


class TestFetchListing:

    @pytest.fixture
    def api_calls(self, monkeypatch, rising_json_text):
        calls = []

        def fake_post(url, auth=None, data=None, headers=None, timeout=None):
            return token_response()

        def fake_get(url, params=None, headers=None, timeout=None):
            calls.append((url, params, headers["Authorization"]))
            return FakeResponse(rising_json_text)

        monkeypatch.setattr(trend_watcher.requests, "post", fake_post)
        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        return calls

    def test_fetch_listing_requests_the_api_with_a_bearer_token(self, api_calls):
        candidates = trend_watcher.fetch_listing("ProgrammerHumor", "top:week")
        url, params, authorization = api_calls[0]
        assert url == "https://oauth.reddit.com/r/ProgrammerHumor/top"
        assert params["t"] == "week"
        assert authorization == "bearer bearer-token"
        assert len(candidates) == 4
        assert len(api_calls) == 1  # scores ride along, no second request

    def test_fetch_rising_uses_the_rising_listing(self, api_calls):
        trend_watcher.fetch_rising("linuxmemes")
        url, params, authorization = api_calls[0]
        assert url == "https://oauth.reddit.com/r/linuxmemes/rising"
        assert "t" not in params


class TestApiGet:

    def test_rate_limit_is_retried(self, monkeypatch, rising_json_text):
        responses = [FakeResponse("rate limited", status_code=429),
                     FakeResponse(rising_json_text)]

        def fake_post(url, auth=None, data=None, headers=None, timeout=None):
            return token_response()

        def fake_get(url, params=None, headers=None, timeout=None):
            return responses.pop(0)

        monkeypatch.setattr(trend_watcher.requests, "post", fake_post)
        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        payload = trend_watcher.api_get("/r/x/rising", {})
        assert payload["data"]["children"]
        assert responses == []

    def test_rejected_token_is_minted_again(self, monkeypatch, rising_json_text):
        minted = []
        responses = [FakeResponse("unauthorized", status_code=401),
                     FakeResponse(rising_json_text)]

        def fake_post(url, auth=None, data=None, headers=None, timeout=None):
            minted.append(url)
            return token_response()

        def fake_get(url, params=None, headers=None, timeout=None):
            return responses.pop(0)

        monkeypatch.setattr(trend_watcher.requests, "post", fake_post)
        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        trend_watcher.api_get("/r/x/rising", {})
        assert len(minted) == 2  # cached token rejected -> minted again

    def test_server_error_propagates(self, monkeypatch):
        def fake_post(url, auth=None, data=None, headers=None, timeout=None):
            return token_response()

        def fake_get(url, params=None, headers=None, timeout=None):
            return FakeResponse("boom", status_code=503)

        monkeypatch.setattr(trend_watcher.requests, "post", fake_post)
        monkeypatch.setattr(trend_watcher.requests, "get", fake_get)
        with pytest.raises(RuntimeError, match="HTTP 503"):
            trend_watcher.api_get("/r/x/rising", {})
