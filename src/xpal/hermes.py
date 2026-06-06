"""Optional Hermes Tweet / Xquik read backend helpers."""

from __future__ import annotations

from typing import Any, Optional

import requests

from .exceptions import AuthenticationError, XApiError
from .pagination import Page

DEFAULT_HERMES_BASE_URL = "https://api.xquik.com"
HERMES_SEARCH_PATH = "/api/v1/x/tweets/search"
_TIMEOUT = 30


def hermes_auth_headers(api_key: str) -> dict[str, str]:
    """Return auth headers for Hermes Tweet / Xquik API keys."""
    if api_key.startswith("xq_"):
        return {"x-api-key": api_key}
    return {"Authorization": f"Bearer {api_key}"}


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_as_dict(item) for item in payload]
    if not isinstance(payload, dict):
        return []

    for key in ("data", "tweets", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [_as_dict(item) for item in value]
        if isinstance(value, dict):
            nested = _extract_items(value)
            if nested:
                return nested
    return []


def _metric(source: dict[str, Any], *keys: str) -> int | None:
    value = _first(source, *keys)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_tweet(tweet: dict[str, Any]) -> dict[str, Any]:
    user = _as_dict(_first(tweet, "user", "author"))
    public_metrics = _as_dict(tweet.get("public_metrics")).copy()
    metric_sources = (tweet, user)
    metric_map = {
        "like_count": ("like_count", "likeCount", "favorites", "favorite_count"),
        "retweet_count": ("retweet_count", "retweetCount", "repost_count", "repostCount"),
        "reply_count": ("reply_count", "replyCount"),
        "quote_count": ("quote_count", "quoteCount"),
        "bookmark_count": ("bookmark_count", "bookmarkCount"),
        "impression_count": ("impression_count", "impressionCount", "view_count", "viewCount"),
    }
    for normalized_key, source_keys in metric_map.items():
        if normalized_key in public_metrics:
            continue
        for source in metric_sources:
            value = _metric(source, *source_keys)
            if value is not None:
                public_metrics[normalized_key] = value
                break

    normalized = {
        "id": str(_first(tweet, "id", "id_str", "tweet_id", "tweetId", "rest_id") or ""),
        "text": _first(tweet, "text", "full_text", "fullText", "content") or "",
        "created_at": _first(tweet, "created_at", "createdAt", "timestamp"),
        "author_id": _first(tweet, "author_id", "authorId", "user_id", "userId") or _first(user, "id", "id_str", "user_id"),
        "conversation_id": _first(tweet, "conversation_id", "conversationId"),
        "lang": tweet.get("lang"),
    }
    if public_metrics:
        normalized["public_metrics"] = public_metrics
    return {key: value for key, value in normalized.items() if value not in (None, "")}


def _next_cursor(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    meta = _as_dict(payload.get("meta"))
    return _first(payload, "next_cursor", "nextCursor", "next_token", "nextToken") or _first(
        meta, "next_cursor", "nextCursor", "next_token", "nextToken"
    )


def search(
    *,
    api_key: str | None,
    base_url: str,
    query: str,
    product: Optional[str],
    count: int,
    cursor: Optional[str],
) -> Page:
    """Search X through Hermes Tweet / Xquik and return an xpal Page."""
    if not api_key:
        raise AuthenticationError(
            "Missing Hermes Tweet / Xquik API key. Set HERMES_TWEET_API_KEY or XQUIK_API_KEY."
        )

    params: dict[str, object] = {
        "q": query,
        "limit": count,
        "queryType": product or "Top",
    }
    if cursor:
        params["cursor"] = cursor

    response = requests.get(
        f"{base_url.rstrip('/')}{HERMES_SEARCH_PATH}",
        headers=hermes_auth_headers(api_key),
        params=params,
        timeout=_TIMEOUT,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = getattr(response, "status_code", None)
        raise XApiError(f"Hermes Tweet / Xquik search failed: {status}", status_code=status) from exc

    payload = response.json()
    return Page(
        [_normalize_tweet(tweet) for tweet in _extract_items(payload)],
        next_cursor=_next_cursor(payload),
    )
