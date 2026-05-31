"""xpal — a Python client library for the X (Twitter) API.

Usage::

    import xpal

    x = xpal.client()                    # credentials from env vars
    x = xpal.client(api_key="...", ...)  # override specific credentials

    # Domain modules
    x.users.get_by_id("123")
    x.users.get_by_username("jack")
    x.users.get_followers("123")

    x.posts.create(text="Hello world")
    x.posts.delete(post_id="456")
    x.posts.like(post_id="789")

    x.timelines.home()
    x.timelines.search("python")
    x.timelines.trends()

    x.bookmarks.list()
    x.bookmarks.add(post_id="456")
"""

from .client import client, XClient
from .exceptions import XPalError, AuthenticationError, RateLimitExceeded, XApiError
from .rate_limiter import RateLimiter
from .pagination import Page


def _read_version() -> str:
    """Resolve the canonical version from the root ``.version`` file (CalVer).

    When running from source/editable installs the file is the source of truth;
    once installed as a wheel we fall back to the version baked into package
    metadata at build time (also derived from ``.version``).
    """
    from pathlib import Path

    version_file = Path(__file__).resolve().parents[2] / ".version"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()

    from importlib.metadata import version, PackageNotFoundError

    try:
        return version("xpal")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _read_version()

__all__ = [
    "client",
    "XClient",
    "RateLimiter",
    "Page",
    "XPalError",
    "AuthenticationError",
    "RateLimitExceeded",
    "XApiError",
    "__version__",
]
