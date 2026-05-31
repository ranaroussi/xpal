"""Pagination + expansion helpers for xpal.

X API list endpoints return a cursor (``meta.next_token``) and expansion
objects (``includes``: referenced users / media / tweets) alongside the data.
The library surfaces both through :class:`Page`, a ``list`` subclass that stays
fully list-compatible (iterate, index, ``len``, JSON-serialize) while carrying
``next_cursor`` and ``includes`` attributes.
"""

# Field/expansion sets requested on reads so callers get useful context.
TWEET_FIELDS = [
    "id", "text", "created_at", "author_id", "public_metrics",
    "conversation_id", "referenced_tweets", "lang",
]
USER_FIELDS = [
    "id", "name", "username", "profile_image_url", "description", "public_metrics",
]
TWEET_EXPANSIONS = ["author_id", "attachments.media_keys", "referenced_tweets.id"]
MEDIA_FIELDS = ["type", "url", "alt_text", "preview_image_url", "duration_ms"]


class Page(list):
    """A list of result dicts that also carries pagination + expansion data.

    Behaves exactly like a ``list``; adds two attributes:

    - ``next_cursor``: token to fetch the next page (``None`` on the last page).
    - ``includes``: expansion objects keyed by type (``users``/``media``/``tweets``).
    """

    __slots__ = ("next_cursor", "includes")

    def __init__(self, items=(), next_cursor=None, includes=None):
        super().__init__(items)
        self.next_cursor = next_cursor
        self.includes = includes or {}


def normalize_includes(includes) -> dict:
    """Convert a tweepy ``includes`` mapping into plain ``dict`` lists."""
    if not includes:
        return {}
    out: dict[str, list] = {}
    for key in ("users", "tweets", "media", "polls", "places"):
        vals = includes.get(key) if isinstance(includes, dict) else None
        if vals:
            out[key] = [getattr(v, "data", v) for v in vals]
    return out


def page(resp) -> Page:
    """Build a :class:`Page` from a tweepy v2 ``Response`` (data + meta + includes)."""
    items = [getattr(x, "data", x) for x in (resp.data or [])]
    meta = getattr(resp, "meta", None) or {}
    includes = normalize_includes(getattr(resp, "includes", None))
    return Page(items, next_cursor=meta.get("next_token"), includes=includes)
