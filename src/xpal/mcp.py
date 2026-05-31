"""xpal MCP server + CLI — both delegate all logic to the xpal library.

Two ways in, one module:

    xpal mcp                          # stdio MCP server
    xpal posts create "hello world"   # call any xp.<namespace>.<method>(...)
    xpal timelines search "python" --product Latest --count 20
    xpal users get_by_username jack

The CLI is a generic dispatcher: `xpal <namespace> <method> <args...>` maps
onto `xp.<namespace>.<method>(...)`. Positional tokens fill positional params
in order; `--flag value` fills keyword params (repeat a flag to build a list).
Argument types are coerced from each method's signature, and the return value
is printed as JSON.
"""

import inspect
import json
import logging
import sys
import warnings

from fastmcp import FastMCP

from .client import client as _make_client, XClient
from .exceptions import XPalError
from .users import Users
from .posts import Posts
from .timelines import Timelines
from .bookmarks import Bookmarks
from .dms import Dms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=SyntaxWarning)

server = FastMCP(name="XMCPServer")

_xp_instance: XClient | None = None


def _get_xp() -> XClient:
    global _xp_instance
    if _xp_instance is None:
        _xp_instance = _make_client()
    return _xp_instance


# ── User Management Tools ────────────────────────────────────────────


@server.tool(name="get_user_profile", description="Get detailed profile information for a user")
async def get_user_profile(user_id: str) -> dict:
    return _get_xp().users.get_by_id(user_id)


@server.tool(name="get_user_by_screen_name", description="Fetches a user by screen name")
async def get_user_by_screen_name(screen_name: str) -> dict:
    return _get_xp().users.get_by_username(screen_name)


@server.tool(name="get_user_by_id", description="Fetches a user by ID")
async def get_user_by_id(user_id: str) -> dict:
    return _get_xp().users.get_by_id(user_id)


@server.tool(name="get_user_followers", description="Retrieves a list of followers for a given user")
async def get_user_followers(user_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().users.get_followers(user_id, count=count, cursor=cursor)


@server.tool(name="get_user_following", description="Retrieves users the given user is following")
async def get_user_following(user_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().users.get_following(user_id, count=count, cursor=cursor)


@server.tool(name="get_me", description="Get the authenticated user's own profile")
async def get_me() -> dict:
    return _get_xp().users.me()


@server.tool(name="lookup_users", description="Batch-fetch up to 100 users by IDs or usernames")
async def lookup_users(ids: list[str] | None = None, usernames: list[str] | None = None) -> list[dict]:
    return _get_xp().users.lookup(ids=ids, usernames=usernames)


@server.tool(name="get_user_posts", description="Get a user's recent posts (their timeline)")
async def get_user_posts(user_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().users.posts(user_id, count=count, cursor=cursor)


@server.tool(name="follow_user", description="Follow a user")
async def follow_user(target_user_id: str) -> dict:
    return _get_xp().users.follow(target_user_id)


@server.tool(name="unfollow_user", description="Unfollow a user")
async def unfollow_user(target_user_id: str) -> dict:
    return _get_xp().users.unfollow(target_user_id)


# ── Post Management Tools ────────────────────────────────────────────


@server.tool(name="post_tweet", description="Post with optional media, reply, quote, community, and tags. reply_to only works in conversations you're part of (X anti-spam rule).")
async def post_tweet(text: str, media_paths: list[str] | None = None, reply_to: str | None = None, quote_to: str | None = None, community_id: str | None = None, tags: list[str] | None = None) -> dict:
    return _get_xp().posts.create(text=text, media_paths=media_paths, reply_to=reply_to, quote_to=quote_to, community_id=community_id, tags=tags)


@server.tool(name="quote_tweet", description="Quote a post with your own commentary")
async def quote_tweet(tweet_id: str, text: str, media_paths: list[str] | None = None, tags: list[str] | None = None) -> dict:
    return _get_xp().posts.quote(post_id=tweet_id, text=text, media_paths=media_paths, tags=tags)


@server.tool(name="repost", description="Repost (retweet) a post")
async def repost(tweet_id: str) -> dict:
    return _get_xp().posts.repost(post_id=tweet_id)


@server.tool(name="unrepost", description="Remove a repost (undo a retweet)")
async def unrepost(tweet_id: str) -> dict:
    return _get_xp().posts.unrepost(post_id=tweet_id)


@server.tool(name="delete_tweet", description="Delete a tweet by its ID")
async def delete_tweet(tweet_id: str) -> dict:
    return _get_xp().posts.delete(post_id=tweet_id)


@server.tool(name="get_tweet_details", description="Get a post with public_metrics (like/reply/repost/quote counts)")
async def get_tweet_details(tweet_id: str) -> dict:
    return _get_xp().posts.get(post_id=tweet_id)


@server.tool(name="get_tweet_replies", description="Get replies to a post (its conversation), for saturation analysis")
async def get_tweet_replies(tweet_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().posts.replies(post_id=tweet_id, count=count, cursor=cursor)


@server.tool(name="get_tweet_likers", description="Get users who liked a post")
async def get_tweet_likers(tweet_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().posts.likers(post_id=tweet_id, count=count, cursor=cursor)


@server.tool(name="get_tweet_reposters", description="Get users who reposted a post")
async def get_tweet_reposters(tweet_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().posts.reposters(post_id=tweet_id, count=count, cursor=cursor)


@server.tool(name="create_poll_tweet", description="Create a tweet with a poll")
async def create_poll_tweet(text: str, choices: list[str], duration_minutes: int) -> dict:
    return _get_xp().posts.create_poll(text=text, choices=choices, duration_minutes=duration_minutes)


@server.tool(name="favorite_tweet", description="Favorites a tweet")
async def favorite_tweet(tweet_id: str) -> dict:
    return _get_xp().posts.like(post_id=tweet_id)


@server.tool(name="unfavorite_tweet", description="Unfavorites a tweet")
async def unfavorite_tweet(tweet_id: str) -> dict:
    return _get_xp().posts.unlike(post_id=tweet_id)


# ── Bookmark Tools ────────────────────────────────────────────────────


@server.tool(name="bookmark_tweet", description="Adds the tweet to bookmarks")
async def bookmark_tweet(tweet_id: str, folder_id: str | None = None) -> dict:
    return _get_xp().bookmarks.add(post_id=tweet_id, folder_id=folder_id)


@server.tool(name="delete_bookmark", description="Removes the tweet from bookmarks")
async def delete_bookmark(tweet_id: str) -> dict:
    return _get_xp().bookmarks.remove(post_id=tweet_id)


@server.tool(
    name="delete_all_bookmarks",
    description="DESTRUCTIVE AND IRREVERSIBLE: Permanently deletes ALL bookmarks one by one. This cannot be undone. Always confirm explicitly with the user before calling this tool.",
)
async def delete_all_bookmarks() -> dict:
    return _get_xp().bookmarks.remove_all()


@server.tool(name="get_bookmarks", description="Retrieves the authenticated user's bookmarked tweets. Requires Basic access tier or higher.")
async def get_bookmarks(count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().bookmarks.list(count=count, cursor=cursor)


# ── Timeline & Search Tools ──────────────────────────────────────────


@server.tool(name="get_timeline", description="Get tweets from your home timeline (For You)")
async def get_timeline(count: int | None = 100, seen_tweet_ids: list[str] | None = None, cursor: str | None = None) -> list[dict]:
    return _get_xp().timelines.home(count=count, seen_post_ids=seen_tweet_ids, cursor=cursor)


@server.tool(name="get_latest_timeline", description="Get tweets from your home timeline (Following)")
async def get_latest_timeline(count: int | None = 100) -> list[dict]:
    return _get_xp().timelines.following(count=count)


@server.tool(name="search", description="Search X with a query")
async def search(query: str, product: str | None = "Top", count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().timelines.search(query=query, product=product, count=count, cursor=cursor)


@server.tool(name="get_trends", description="Retrieves trending topics on X")
async def get_trends(category: str | None = None, count: int | None = 50) -> list[dict]:
    return _get_xp().timelines.trends(category=category, count=count)


@server.tool(name="get_list_timeline", description="Get posts from a specific List's timeline")
async def get_list_timeline(list_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().timelines.list_posts(list_id=list_id, count=count, cursor=cursor)


@server.tool(name="get_user_mentions", description="Get tweets mentioning a specific user")
async def get_user_mentions(user_id: str, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().timelines.mentions(user_id=user_id, count=count, cursor=cursor)


# ── Direct Message Tools ──────────────────────────────────────────────


@server.tool(name="send_dm", description="Send a direct message to a user")
async def send_dm(participant_id: str, text: str, media_id: str | None = None) -> dict:
    return _get_xp().dms.send(participant_id=participant_id, text=text, media_id=media_id)


@server.tool(name="get_dms", description="Read direct message events. Requires the dm.read scope (separately gated by X).")
async def get_dms(participant_id: str | None = None, count: int | None = 100, cursor: str | None = None) -> list[dict]:
    return _get_xp().dms.list(participant_id=participant_id, count=count, cursor=cursor)


# ── CLI ───────────────────────────────────────────────────────────────

# Domain namespaces exposed on the CLI, mapped to their classes for help/introspection.
_NAMESPACES = {
    "users": Users,
    "posts": Posts,
    "timelines": Timelines,
    "bookmarks": Bookmarks,
    "dms": Dms,
}


def _public_methods(cls) -> list[str]:
    return [n for n in dir(cls) if not n.startswith("_")]


def _wants_list(annotation) -> bool:
    return "list" in str(annotation).lower()


def _coerce(value, annotation):
    """Coerce a raw CLI string (or list of strings) to the param's type."""
    ann = str(annotation)
    if _wants_list(annotation):
        items = value if isinstance(value, list) else [value]
        return [int(x) for x in items] if "int" in ann else items
    if isinstance(value, list):  # repeated flag for a non-list param → take last
        value = value[-1]
    if "int" in ann:
        return int(value)
    if "bool" in ann:
        return str(value).lower() in ("1", "true", "yes", "y")
    return value


def _parse_args(tokens: list[str]) -> tuple[list[str], dict]:
    """Split CLI tokens into positionals and --flag kwargs (repeats → list)."""
    positionals: list[str] = []
    kwargs: dict = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            key = tok[2:].replace("-", "_")
            if i + 1 >= len(tokens):
                raise SystemExit(f"error: flag --{key} expects a value")
            val = tokens[i + 1]
            if key in kwargs:
                existing = kwargs[key]
                kwargs[key] = existing + [val] if isinstance(existing, list) else [existing, val]
            else:
                kwargs[key] = val
            i += 2
        else:
            positionals.append(tok)
            i += 1
    return positionals, kwargs


def _invoke(namespace: str, method: str, tokens: list[str]):
    ns_obj = getattr(_get_xp(), namespace)
    func = getattr(ns_obj, method)
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    by_name = {p.name: p for p in params}

    positionals, kwargs = _parse_args(tokens)

    args = [_coerce(val, param.annotation) for val, param in zip(positionals, params)]
    coerced_kwargs = {}
    for key, val in kwargs.items():
        if key not in by_name:
            raise SystemExit(f"error: {namespace} {method} has no parameter '{key}'")
        coerced_kwargs[key] = _coerce(val, by_name[key].annotation)

    return func(*args, **coerced_kwargs)


def _usage() -> str:
    lines = [
        "xpal — X (Twitter) API client",
        "",
        "Usage:",
        "  xpal mcp                                 start the stdio MCP server",
        "  xpal <namespace> <method> [args] [--flag value]",
        "",
        "Namespaces & methods:",
    ]
    for name, cls in _NAMESPACES.items():
        lines.append(f"  {name}: {', '.join(_public_methods(cls))}")
    lines += [
        "",
        "Examples:",
        '  xpal posts create "hello world"',
        '  xpal posts create "with tags" --tags python --tags x',
        '  xpal timelines search "python" --product Latest --count 20',
        "  xpal users get_by_username jack",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    """Unified entry point: `xpal mcp` runs the server, everything else is a call."""
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_usage())
        return

    if argv[0] == "mcp":
        server.run()
        return

    if len(argv) < 2 or argv[0] not in _NAMESPACES:
        print(_usage(), file=sys.stderr)
        raise SystemExit(2)

    namespace, method, *rest = argv
    if method not in _public_methods(_NAMESPACES[namespace]):
        print(f"error: unknown method '{namespace} {method}'\n", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        raise SystemExit(2)

    try:
        result = _invoke(namespace, method, rest)
    except XPalError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
