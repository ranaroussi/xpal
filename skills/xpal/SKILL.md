---
name: xpal
description: Use xpal as a Python client library, CLI, and stdio MCP server for the X (Twitter) API — construct one client, reach domain namespaces (users, posts, timelines, bookmarks, dms), with credential resolution, lazy dual-version sessions, and built-in rate limiting. Covers library usage, the reflection CLI, the MCP server, credentials/config, rate limits, and the real X API constraints (reply restrictions, communities post-only, DM read scope).
---

# xpal

## When to use this skill

Use this skill when you need to read from or write to the X (Twitter) API from Python, a shell, or an MCP-capable agent: look up users and followers, publish/quote/repost/reply to posts, read home/list/search timelines, manage bookmarks, send/read DMs, or run any of these as CLI commands or MCP tools.

## What xpal is

`xpal` is a thin, opinionated client over [Tweepy](https://www.tweepy.org/) that ships three faces from one install:

- **Library** — `import xpal; x = xpal.client()`, then `x.<namespace>.<method>()`.
- **CLI** — `xpal <namespace> <method> [args] [--flags]`, reflected straight onto the library.
- **MCP server** — `xpal mcp`, a stdio server exposing every method as a tool.

`import xpal` never imports the MCP server, so library-only use stays lean.

Design notes that matter when using it:

- Credentials resolve **once per client**, precedence **explicit kwarg > `TWITTER_*` env > `X_*` env**. No module-level globals.
- Sessions are lazy and cached: v2 (`tweepy.Client`) for most calls, v1.1 (`tweepy.API`) only for media upload + trends, OAuth 2.0 user-context only for bookmarks.
- Every read returns a plain `dict` or `list[dict]` — no bespoke model classes.
- Write/engagement calls pass through a local `RateLimiter` that raises before you spend a request.
- **No simulated/mock methods exist.** Anything the X API cannot actually back is absent by design.

## Install

```bash
pip install xpal
```

Python 3.10+. One install provides the library, the `xpal` CLI, and the MCP server.

## Credentials

Set whichever credential set you have; `xpal.client()` reads them from the environment, or you can pass them explicitly.

| Client param | `TWITTER_*` env | `X_*` env | Needed for |
|---|---|---|---|
| `api_key` | `TWITTER_API_KEY` | `X_CONSUMER_KEY` | everything |
| `api_secret` | `TWITTER_API_SECRET` | `X_CONSUMER_KEY_SECRET` | everything |
| `access_token` | `TWITTER_ACCESS_TOKEN` | `X_ACCESS_TOKEN` | everything |
| `access_token_secret` | `TWITTER_ACCESS_TOKEN_SECRET` | `X_ACCESS_TOKEN_SECRET` | everything |
| `bearer_token` | `TWITTER_BEARER_TOKEN` | `X_BEARER_TOKEN` | v2 reads/writes |
| `oauth2_access_token` | `TWITTER_OAUTH2_USER_ACCESS_TOKEN` | `X_AUTH2_ACCESS_TOKEN` | bookmarks |

```python
import xpal

x = xpal.client()                          # all from env
x = xpal.client(bearer_token="AAAA...")    # override one, rest from env
x = xpal.client(                           # fully explicit
    api_key="...", api_secret="...",
    access_token="...", access_token_secret="...",
    bearer_token="...",
)
```

A `.env` file is auto-loaded by the CLI/MCP server (via `python-dotenv`); for the library, load it yourself or export the vars.

## Library usage

Construct once, reach for a namespace, get back plain dicts. List methods return a `Page` (a `list` subclass) carrying `.next_cursor` (pass back as `cursor` for the next page) and `.includes` (expansion objects keyed by `users`/`tweets`/`media`). Over MCP, paginated tools return `{"data", "next_cursor", "includes"}`.

```python
import xpal
x = xpal.client()

# ── users ──────────────────────────────────────────────
x.users.me()                                   # the authenticated account
x.users.get_by_id("2244994945")
x.users.get_by_username("jack")
x.users.lookup(usernames=["jack", "elonmusk"]) # batch, up to 100 (ids= OR usernames=)
x.users.get_followers("2244994945", count=100) # Page (.next_cursor / .includes)
x.users.get_following("2244994945")
x.users.posts("2244994945")                    # a user's recent posts (+public_metrics)
x.users.follow("2244994945")
x.users.unfollow("2244994945")
x.users.mute("2244994945")                     # mute/unmute (no block/unblock in API v2)
x.users.unmute("2244994945")
x.users.get_muted()                            # accounts you've muted
x.users.get_blocked()                          # accounts you've blocked

# ── posts ──────────────────────────────────────────────
x.posts.create(text="Hello world")
x.posts.create(text="With media + tags", media_paths=["./cat.jpg"], tags=["python"])
x.posts.create(text="Image + alt", media_paths=["./cat.jpg"], media_alt_texts=["a cat"])
x.posts.create(text="With video", media_paths=["./clip.mp4"])  # .gif/.mp4/.mov chunked
x.posts.create(text="A reply", reply_to="1700000000000000000")
x.posts.create(text="Into a community", community_id="1493446837214187523")
x.posts.quote("1700000000000000000", text="great take")
x.posts.repost("1700000000000000000")
x.posts.unrepost("1700000000000000000")
x.posts.get("1700000000000000000")             # public_metrics + includes
x.posts.get_many(["1700000000000000000", "..."])  # batch up to 100
x.posts.replies("1700000000000000000")         # conversation, for saturation analysis
x.posts.quotes("1700000000000000000")          # posts quoting this one (count 10–100)
x.posts.likers("1700000000000000000")
x.posts.reposters("1700000000000000000")
x.posts.like("1700000000000000000")
x.posts.unlike("1700000000000000000")
x.posts.delete("1700000000000000000")
x.posts.create_poll(text="Tabs or spaces?", choices=["Tabs", "Spaces"], duration_minutes=1440)

# ── timelines ──────────────────────────────────────────
x.timelines.home(count=50)                     # algorithmic "For You"
x.timelines.following(count=50)                # reverse-chronological
x.timelines.list_posts("1234567890")           # a curated List's feed
x.timelines.search("from:jack web3", product="Top")
x.timelines.mentions("2244994945")
x.timelines.trends()                           # worldwide (v1.1, WOEID 1)

# ── bookmarks (needs OAuth 2.0 user-context token) ─────
x.bookmarks.list(count=100)
x.bookmarks.add("1700000000000000000")
x.bookmarks.remove("1700000000000000000")
x.bookmarks.remove_all()                       # DESTRUCTIVE: deletes every bookmark

# ── dms ────────────────────────────────────────────────
x.dms.send(participant_id="2244994945", text="hey!")
x.dms.list(participant_id="2244994945")        # read requires the dm.read scope
```

### Version

```python
import xpal
xpal.__version__        # CalVer string, e.g. "0.20260531.0"
```

## CLI usage

`xpal` reflects onto the library — no hand-written command per method. Positional tokens fill positional params in order; `--flag value` fills keyword params, and repeating a flag builds a list. `int`/`bool`/`list` params are coerced from the method signature; results print as JSON. Credentials come from the same env vars.

```bash
xpal users get_by_username jack
xpal posts create "hello world"
xpal posts create "with media + tags" --media_paths ./cat.jpg --tags python --tags x
xpal timelines search "from:jack" --product Latest --count 20
xpal posts delete 1700000000000000000
xpal dms send 2244994945 "hey there"

xpal            # or `xpal --help` — prints every namespace and its methods
xpal mcp        # start the stdio MCP server through the same binary
```

## MCP server usage

`xpal mcp` starts a stdio MCP server. Register it with an MCP-capable agent (the command is `xpal mcp`, transport stdio), with credentials provided via the environment or a `.env` file. Every namespace method is exposed as a tool (e.g. `post_tweet`, `quote_tweet`, `repost`, `get_tweet_details`, `get_tweet_replies`, `follow_user`, `get_list_timeline`, `send_dm`, `get_dms`, `get_bookmarks`).

## Rate limiting

Write/engagement calls run through a fixed-window `RateLimiter` mirroring X's documented ceilings, so you hit `RateLimitExceeded` locally instead of spending a request to learn you're throttled.

| Bucket | Limit | Window |
|---|---|---|
| `post_actions` | 300 | 15 min |
| `dm_actions` | 1000 | 15 min |
| `follow_actions` | 400 | 24 h |
| `like_actions` | 1000 | 24 h |

```python
from xpal import RateLimiter, RateLimitExceeded
from datetime import timedelta

limiter = RateLimiter(limits={"post_actions": {"limit": 5, "window": timedelta(minutes=1)}})
x = xpal.client(rate_limiter=limiter)

try:
    x.posts.create(text="...")
except RateLimitExceeded as e:
    print(f"{e.action_type} resets at {e.reset_at}")
```

`check(action_type)` is side-effect-free; `consume(action_type)` counts and raises in one step.

## Exceptions

```
XPalError                 # base — catch this to catch everything
├── AuthenticationError   # missing/invalid creds; message names the absent token + env var
├── XApiError             # X API returned an error; clean one-line message + .status_code
└── RateLimitExceeded     # .action_type, .reset_at
```

Asking for a surface without the required credential tier (e.g. bookmarks without an OAuth 2.0 token) raises a precise `AuthenticationError` naming the missing token and env var, not a deep 401.

## Real X API constraints (not xpal limitations)

- **Replies are restricted.** `posts.create(reply_to=...)` only succeeds when the authenticated account is allowed into that conversation — the original post must @mention you, or be a reply to one of your posts. Replying to an arbitrary stranger's post via the API fails as an anti-spam measure, even though the call is well-formed.
- **Communities are post-only.** You can publish into a Community with `posts.create(community_id=...)`, but the X API v2 has no endpoint to read a Community timeline — there is no `timelines.community(...)`. Use a List or search as a workaround.
- **DM reads are scope-gated.** `dms.list(...)` requires the `dm.read` scope, which X grants separately; confirm your access tier before relying on it.
- **Bookmarks need OAuth 2.0** user-context token (`bookmark.read`/`users.read` scopes) and Basic access tier or higher.
