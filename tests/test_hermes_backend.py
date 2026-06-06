from __future__ import annotations

import pytest

import xpal
from xpal.exceptions import AuthenticationError


class Response:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("request failed")

    def json(self) -> dict:
        return self._payload


def test_hermes_search_uses_x_api_key_header(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append((url, headers, params, timeout))
        return Response(
            {
                "data": [
                    {
                        "id": "1",
                        "text": "hello",
                        "author": {"id": "42"},
                        "likeCount": 3,
                        "replyCount": 2,
                    }
                ],
                "meta": {"next_cursor": "next"},
            }
        )

    monkeypatch.setattr("xpal.hermes.requests.get", fake_get)
    xp = xpal.client(read_backend="hermes", hermes_api_key="xq_test", hermes_base_url="https://example.test")

    page = xp.timelines.search("from:jack", product="Latest", count=1, cursor="cursor")

    assert calls == [
        (
            "https://example.test/api/v1/x/tweets/search",
            {"x-api-key": "xq_test"},
            {"q": "from:jack", "limit": 10, "queryType": "Latest", "cursor": "cursor"},
            30,
        )
    ]
    assert page.next_cursor == "next"
    assert page == [
        {
            "id": "1",
            "text": "hello",
            "author_id": "42",
            "public_metrics": {"like_count": 3, "reply_count": 2},
        }
    ]


def test_hermes_search_uses_bearer_header(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append(headers)
        return Response({"tweets": [{"tweetId": "9", "fullText": "bearer"}]})

    monkeypatch.setattr("xpal.hermes.requests.get", fake_get)
    xp = xpal.client(read_backend="hermes", hermes_api_key="token")

    assert xp.timelines.search("python") == [{"id": "9", "text": "bearer"}]
    assert calls == [{"Authorization": "Bearer token"}]


def test_hermes_search_requires_key() -> None:
    xp = xpal.client(read_backend="hermes")

    with pytest.raises(AuthenticationError, match="HERMES_TWEET_API_KEY or XQUIK_API_KEY"):
        xp.timelines.search("python")
