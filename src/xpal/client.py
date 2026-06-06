"""xpal client — the central object that holds sessions and domain modules.

Usage::

    xp = xpal.client()                       # reads credentials from env
    xp = xpal.client(api_key="...", ...)      # override specific credentials

    xp.users.get_by_id("123")
    xp.posts.create(text="Hello world")
    xp.timelines.search("python")
    xp.bookmarks.list()
"""

import os
import logging
import functools
from datetime import datetime
from typing import Optional

import requests
import tweepy

from .exceptions import AuthenticationError, XApiError
from .hermes import DEFAULT_HERMES_BASE_URL
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_API_TIMEOUT = 30  # seconds


def _translate_api_error(exc: Exception) -> XApiError:
    """Turn a Tweepy/HTTP error into a clean, single-line :class:`XApiError`."""
    status = None
    detail = ""
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)

    if isinstance(exc, tweepy.errors.TweepyException):
        # Tweepy stringifies as e.g. "400 Bad Request\n<detail>"; collapse it.
        detail = " ".join(str(exc).split())
    elif isinstance(exc, requests.HTTPError):
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("title") or ""
        except Exception:
            detail = ""
        reason = getattr(response, "reason", "") or ""
        detail = " ".join(f"{status or ''} {reason} {detail}".split())
    else:
        detail = " ".join(str(exc).split())

    reset_at = None
    if status == 429 and response is not None:
        header = getattr(response, "headers", {}) or {}
        raw_reset = header.get("x-rate-limit-reset")
        if raw_reset:
            try:
                reset_at = datetime.fromtimestamp(int(raw_reset))
            except (ValueError, TypeError, OSError):
                reset_at = None

    return XApiError(detail or "X API request failed", status_code=status, reset_at=reset_at)


class _SessionProxy:
    """Wraps a Tweepy session so API errors surface as :class:`XApiError`.

    Attribute access is transparent; only callables are wrapped so that any
    ``TweepyException`` raised by a request is translated into xpal's hierarchy.
    """

    def __init__(self, target):
        object.__setattr__(self, "_target", target)

    def __getattr__(self, name):
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr

        @functools.wraps(attr)
        def wrapper(*args, **kwargs):
            try:
                return attr(*args, **kwargs)
            except tweepy.errors.TweepyException as exc:
                raise _translate_api_error(exc) from exc

        return wrapper


def _resolve_credential(explicit: Optional[str], tw_env: str, x_env: str) -> Optional[str]:
    """Return explicit value if given, else fall back to env vars.

    Accepts both the ``TWITTER_*`` prefix (back-compat) and the ``X_*`` prefix.
    """
    if explicit is not None:
        return explicit
    return os.getenv(tw_env) or os.getenv(x_env)


class XClient:
    """Holds authenticated tweepy sessions and exposes domain modules.

    Construct via :func:`xpal.client` — not directly.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        bearer_token: Optional[str] = None,
        oauth2_access_token: Optional[str] = None,
        read_backend: Optional[str] = None,
        hermes_api_key: Optional[str] = None,
        hermes_base_url: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        # Resolve credentials: explicit param > TWITTER_ env > X_ env
        self._api_key = _resolve_credential(api_key, "TWITTER_API_KEY", "X_CONSUMER_KEY")
        self._api_secret = _resolve_credential(api_secret, "TWITTER_API_SECRET", "X_CONSUMER_KEY_SECRET")
        self._access_token = _resolve_credential(access_token, "TWITTER_ACCESS_TOKEN", "X_ACCESS_TOKEN")
        self._access_token_secret = _resolve_credential(access_token_secret, "TWITTER_ACCESS_TOKEN_SECRET", "X_ACCESS_TOKEN_SECRET")
        self._bearer_token = _resolve_credential(bearer_token, "TWITTER_BEARER_TOKEN", "X_BEARER_TOKEN")
        self._oauth2_access_token = _resolve_credential(oauth2_access_token, "TWITTER_OAUTH2_USER_ACCESS_TOKEN", "X_AUTH2_ACCESS_TOKEN")
        self._read_backend = read_backend if read_backend is not None else os.getenv("X_READ_BACKEND")
        self._hermes_api_key = (
            hermes_api_key
            if hermes_api_key is not None
            else os.getenv("HERMES_TWEET_API_KEY") or os.getenv("XQUIK_API_KEY")
        )
        self._hermes_base_url = (
            hermes_base_url
            if hermes_base_url is not None
            else os.getenv("HERMES_TWEET_BASE_URL") or os.getenv("XQUIK_BASE_URL") or DEFAULT_HERMES_BASE_URL
        )

        self._rate_limiter = rate_limiter or RateLimiter()

        # Lazy-initialized tweepy clients
        self._v2_client: Optional[tweepy.Client] = None
        self._v1_api: Optional[tweepy.API] = None

        # Domain modules (initialized lazily to avoid circular import at module level)
        self._users = None
        self._posts = None
        self._timelines = None
        self._bookmarks = None
        self._dms = None

    # ── Credential validation ──────────────────────────────────────────

    def _require_oauth1(self) -> None:
        """Ensure OAuth 1.0a credentials are present."""
        missing = []
        if not self._api_key:
            missing.append("api_key")
        if not self._api_secret:
            missing.append("api_secret")
        if not self._access_token:
            missing.append("access_token")
        if not self._access_token_secret:
            missing.append("access_token_secret")
        if missing:
            raise AuthenticationError(
                f"Missing required OAuth 1.0a credentials: {', '.join(missing)}. "
                "Pass them to xpal.client() or set the corresponding env vars."
            )

    def _require_bearer(self) -> None:
        if not self._bearer_token:
            raise AuthenticationError(
                "Missing bearer_token. Pass it to xpal.client() or set "
                "TWITTER_BEARER_TOKEN / X_BEARER_TOKEN."
            )

    def _has_x_search_credentials(self) -> bool:
        return all(
            (
                self._api_key,
                self._api_secret,
                self._access_token,
                self._access_token_secret,
                self._bearer_token,
            )
        )

    def _use_hermes_search(self) -> bool:
        backend = (self._read_backend or "").lower()
        if backend in ("hermes", "xquik"):
            return True
        if backend in ("", "x", "twitter"):
            return bool(self._hermes_api_key and not self._has_x_search_credentials())
        return False

    def _hermes_search(self, *, query: str, product: Optional[str], count: int, cursor: Optional[str]):
        from .hermes import search

        return search(
            api_key=self._hermes_api_key,
            base_url=self._hermes_base_url,
            query=query,
            product=product,
            count=count,
            cursor=cursor,
        )

    def _require_oauth2(self) -> None:
        if not self._oauth2_access_token:
            raise AuthenticationError(
                "Missing oauth2_access_token. Obtain one via the PKCE authorization "
                "flow with bookmark.read, users.read scopes and pass to xpal.client() "
                "or set TWITTER_OAUTH2_USER_ACCESS_TOKEN / X_AUTH2_ACCESS_TOKEN."
            )

    # ── Tweepy session accessors ───────────────────────────────────────

    @property
    def v2(self) -> tweepy.Client:
        """Return (and lazily init) the X v2 API client."""
        if self._v2_client is None:
            self._require_oauth1()
            self._require_bearer()
            self._v2_client = _SessionProxy(tweepy.Client(
                consumer_key=self._api_key,
                consumer_secret=self._api_secret,
                access_token=self._access_token,
                access_token_secret=self._access_token_secret,
                bearer_token=self._bearer_token,
            ))
        return self._v2_client

    @property
    def v1(self) -> tweepy.API:
        """Return (and lazily init) the X v1.1 API (media upload, trends)."""
        if self._v1_api is None:
            self._require_oauth1()
            auth = tweepy.OAuth1UserHandler(
                consumer_key=self._api_key,
                consumer_secret=self._api_secret,
                access_token=self._access_token,
                access_token_secret=self._access_token_secret,
            )
            self._v1_api = _SessionProxy(tweepy.API(auth))
        return self._v1_api

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    # ── OAuth 2.0 helpers (bookmarks) ──────────────────────────────────

    def _get_oauth2_headers_and_user_id(self) -> tuple[dict, str]:
        """Resolve OAuth 2.0 Authorization headers and the authenticated user ID.

        Used by bookmarks endpoints that require OAuth 2.0 User Context.
        """
        self._require_oauth2()
        headers = {"Authorization": f"Bearer {self._oauth2_access_token}"}
        resp = requests.get(
            "https://api.x.com/2/users/me",
            headers=headers,
            timeout=_API_TIMEOUT,
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise _translate_api_error(exc) from exc
        return headers, resp.json()["data"]["id"]

    def _bookmarks_request(
        self,
        method: str,
        headers: dict,
        user_id: str,
        tweet_id: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> dict:
        url = f"https://api.x.com/2/users/{user_id}/bookmarks"
        if tweet_id:
            url += f"/{tweet_id}"
        resp = requests.request(
            method, url, headers=headers, params=params or {}, timeout=_API_TIMEOUT
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise _translate_api_error(exc) from exc
        return resp.json()

    def _bookmark_folders_request(
        self,
        headers: dict,
        user_id: str,
        folder_id: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> dict:
        url = f"https://api.x.com/2/users/{user_id}/bookmarks/folders"
        if folder_id:
            url += f"/{folder_id}"
        resp = requests.get(
            url, headers=headers, params=params or {}, timeout=_API_TIMEOUT
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise _translate_api_error(exc) from exc
        return resp.json()

    # ── Domain accessors ───────────────────────────────────────────────

    @property
    def users(self):
        if self._users is None:
            from .users import Users
            self._users = Users(self)
        return self._users

    @property
    def posts(self):
        if self._posts is None:
            from .posts import Posts
            self._posts = Posts(self)
        return self._posts

    @property
    def timelines(self):
        if self._timelines is None:
            from .timelines import Timelines
            self._timelines = Timelines(self)
        return self._timelines

    @property
    def bookmarks(self):
        if self._bookmarks is None:
            from .bookmarks import Bookmarks
            self._bookmarks = Bookmarks(self)
        return self._bookmarks

    @property
    def dms(self):
        if self._dms is None:
            from .dms import Dms
            self._dms = Dms(self)
        return self._dms


def client(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    access_token: Optional[str] = None,
    access_token_secret: Optional[str] = None,
    bearer_token: Optional[str] = None,
    oauth2_access_token: Optional[str] = None,
    read_backend: Optional[str] = None,
    hermes_api_key: Optional[str] = None,
    hermes_base_url: Optional[str] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> XClient:
    """Create an :class:`XClient` instance.

    All parameters are optional — if omitted, they are read from environment
    variables (``TWITTER_*`` or ``X_*`` prefixes).

    Returns:
        An authenticated :class:`XClient` with ``.users``, ``.posts``,
        ``.timelines``, and ``.bookmarks`` domain modules.
    """
    return XClient(
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        bearer_token=bearer_token,
        oauth2_access_token=oauth2_access_token,
        read_backend=read_backend,
        hermes_api_key=hermes_api_key,
        hermes_base_url=hermes_base_url,
        rate_limiter=rate_limiter,
    )
