# xpal

A tiny, batteries-included Python client for the **X (Twitter) API** — one `xpal.client()`, five clean domain namespaces (`users` · `posts` · `timelines` · `bookmarks` · `dms`), built-in rate limiting, a **CLI**, and a bundled **MCP server** so any AI client can drive X over stdio. No globals, no env-var juggling, no per-call client wiring.

[![License: MIT](https://img.shields.io/badge/license-MIT-orange.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logoColor=white)](./pyproject.toml)
[![PyPI](https://img.shields.io/pypi/v/xpal?color=green)](https://pypi.org/project/xpal/)
[![MCP](https://img.shields.io/badge/MCP-ready-black?logoColor=white)](#mcp-server--drive-x-with-an-ai)
[![Follow @aroussi](https://img.shields.io/twitter/follow/aroussi.svg)](https://x.com/aroussi)

**Tweepy handles the wire protocol, auth handshakes, and v1.1/v2 plumbing. xpal owns everything you'd otherwise hand-roll on top** — credential resolution, lazy session management, a domain-grouped API surface, rate-limit accounting, a typed exception hierarchy, and a drop-in MCP adapter.

**Jump to:** [Quickstart](#quickstart) · [Library](#the-library) · [CLI](#a-cli-that-mirrors-the-library) · [Drive X with an AI](#mcp-server--drive-x-with-an-ai) · [API](#api) · [Configuration](#configuration)

---

## Contents

- [Features](#features)
- [Quickstart](#quickstart)
- [Install](#install)
- [The library](#the-library)
- [Why xpal](#why-xpal)
- [The CLI](#a-cli-that-mirrors-the-library)
- [What makes xpal different](#what-makes-xpal-different)
- [Architecture](#architecture)
- [API](#api)
- [Configuration](#configuration)
- [Development](#development)
- [Project layout](#project-layout)
- [License](#license)

## Features

| Feature | What you get | Where |
|---|---|---|
| **One client, five namespaces** | `x = xpal.client()` then `x.users`, `x.posts`, `x.timelines`, `x.bookmarks`, `x.dms`. No re-instantiating a client per call, no passing tokens around. | [below](#the-library) |
| **Constructor injection over globals** | Pass credentials explicitly *or* let them resolve from the environment. The library never reaches into `os.environ` behind your back — the same client is safe to construct many times with different creds. | [below](#credentials-without-the-globals) |
| **Dual env-var prefixes** | Reads both `TWITTER_*` (Tweepy-native / back-compat) and `X_*` names, explicit param always wins. Drop it into an existing Tweepy setup with zero migration. | [Configuration](#configuration) |
| **Lazy, dual-version sessions** | v2 (`tweepy.Client`) and v1.1 (`tweepy.API`, for media upload + trends) are built on first use and cached — and only the auth tier a call actually needs is validated. | [below](#lazy-dual-version-sessions) |
| **Built-in rate limiting** | A fixed-window counter mirrors X's documented per-action limits and raises `RateLimitExceeded` *before* you burn a request. Pluggable — swap in Redis for multi-process deployments. | [below](#rate-limiting-that-fails-before-the-api-does) |
| **Typed exceptions** | `XPalError` → `AuthenticationError`, `RateLimitExceeded`. Catch what you care about; missing-credential errors tell you exactly which token and env var is absent. | [API](#exceptions) |
| **Unified CLI** | `xpal <namespace> <method> [args]` maps onto any library call and prints JSON — no per-command boilerplate. `xpal mcp` starts the server. | [below](#a-cli-that-mirrors-the-library) |
| **Built-in MCP server** | The same library, exposed as Model Context Protocol tools over stdio via `xpal mcp`. Wire it into Claude Desktop, Cursor, Zed, Goose, or anything that speaks MCP. | [below](#mcp-server--drive-x-with-an-ai) |
| **One install, three faces** | `pip install xpal` gives you the library, the `xpal` CLI, and the MCP server — no extras to remember. `import xpal` itself never imports the server, so library-only use stays lean. | [Install](#install) |

## Quick setup — tell your agent about xpal

Copy the block below and paste it into your Pi, OpenClaw, Claude Code, or similar agent harness. It will install xpal, read the skill reference, and know how to use xpal in your software or as an MCP/CLI tool.

```text
Set up xpal so you can drive the X (Twitter) API for me.

1. Install it:  pip install xpal
2. Read the skill reference and follow it as your source of truth:
   https://github.com/ranaroussi/xpal/blob/main/skills/xpal/SKILL.md
3. Credentials come from the environment (TWITTER_* or X_* vars). Do not hardcode them.

xpal gives you three ways to use it — pick whichever fits the task:
- Library:  import xpal; x = xpal.client(); then x.<namespace>.<method>()
- CLI:      xpal <namespace> <method> [args] [--flags]   (prints JSON)
- MCP:      xpal mcp   (stdio MCP server; register it and call its tools)

Namespaces: users, posts, timelines, bookmarks, dms.
Reads return plain dicts. Write/engagement calls are rate-limited locally and
raise RateLimitExceeded before hitting the API.

Respect the real X API constraints (these are not bugs):
- Replies only work inside conversations the account is part of (anti-spam).
- Communities are post-only — there is no endpoint to read a community timeline.
- Reading DMs requires the separately-gated dm.read scope.
- Bookmarks require an OAuth 2.0 user-context token.

There is no simulated or mock functionality — if a capability isn't exposed, the
X API genuinely doesn't support it.
```

## Quickstart

```bash
pip install xpal
```

```python
import xpal

# Credentials resolve from env (TWITTER_* or X_*). Or pass them explicitly.
x = xpal.client()

me = x.users.get_by_username("jack")
print(me["id"], me["name"])

for post in x.timelines.search("python", product="Latest", count=20):
    print(post["id"], post["text"][:80])
```

That's the whole arc: construct once, reach for the namespace you want, get back plain dicts.

## Install

```bash
pip install xpal           # library + `xpal` CLI + MCP server, one shot
```

From source:

```bash
git clone https://github.com/ranaroussi/xpal && cd xpal
pip install -e ".[dev]"
```

Python 3.10+.

## The library

```python
import xpal

x = xpal.client()

# ── Users ──────────────────────────────────────────────
x.users.me()                                     # the authenticated account
x.users.get_by_id("2244994945")
x.users.get_by_username("jack")
x.users.lookup(usernames=["jack", "elonmusk"])   # batch, up to 100
x.users.get_followers("2244994945", count=100)
x.users.get_following("2244994945")
x.users.posts("2244994945")                      # a user's recent posts (+metrics)
x.users.follow("2244994945")
x.users.unfollow("2244994945")

# ── Posts ──────────────────────────────────────────────
x.posts.create(text="Hello world")
x.posts.create(text="With a picture", media_paths=["./cat.jpg"])
x.posts.create(text="A reply", reply_to="1700000000000000000")
x.posts.quote("1700000000000000000", text="great take")
x.posts.repost("1700000000000000000")
x.posts.unrepost("1700000000000000000")
x.posts.get(post_id="1700000000000000000")       # includes public_metrics
x.posts.replies("1700000000000000000")           # conversation, for saturation
x.posts.likers("1700000000000000000")
x.posts.reposters("1700000000000000000")
x.posts.like(post_id="1700000000000000000")
x.posts.delete(post_id="1700000000000000000")
x.posts.create_poll(text="Tabs or spaces?", choices=["Tabs", "Spaces"], duration_minutes=1440)
```

> [!NOTE]
> **Replies are restricted by X.** `reply_to` only succeeds when the authenticated account is allowed into that conversation — i.e. the original post **@mentions you**, or the post you're replying to is itself a reply to one of *your* posts. Replying to an arbitrary stranger's post via the API is blocked by X as an anti-spam measure, and will fail even though the call is well-formed.

```python
# ── Timelines & search ─────────────────────────────────
x.timelines.home(count=50)                       # algorithmic "For You"
x.timelines.following(count=50)                  # reverse-chronological
x.timelines.list_posts("1234567890")             # a curated List's feed
x.timelines.search("from:jack web3", product="Top")
x.timelines.mentions("2244994945")
x.timelines.trends()                             # worldwide

# ── Bookmarks (OAuth 2.0 user context) ─────────────────
x.bookmarks.list(count=100)
x.bookmarks.add(post_id="1700000000000000000")
x.bookmarks.remove(post_id="1700000000000000000")

# ── Direct messages (dm.read scope is separately gated) ─
x.dms.send(participant_id="2244994945", text="hey!")
x.dms.list(participant_id="2244994945")
```

Every read returns a plain `dict` (or `list[dict]`); there are no bespoke model classes to learn.

### Credentials without the globals

The original Twitter MCP server reached into `os.getenv` from module-level singletons — fine for one process, a footgun the moment you want two clients or a unit test. xpal resolves credentials **once, per client, with a clear precedence**:

```
explicit kwarg  >  TWITTER_* env var  >  X_* env var
```

```python
# All from env
x = xpal.client()

# Override just the bearer token, leave the rest to env
x = xpal.client(bearer_token="AAAA...")

# Fully explicit — nothing touches the environment
x = xpal.client(
    api_key="...", api_secret="...",
    access_token="...", access_token_secret="...",
    bearer_token="...",
)
```

### Lazy, dual-version sessions

X's API is split across two versions, and xpal hides the seam. The v2 client (`tweepy.Client`) backs almost everything; the v1.1 API (`tweepy.API`) is used only where v2 has no equivalent — **media upload** and **trends**. Both are constructed on first access and cached on the client, and each call only validates the credential tier it actually needs:

| Surface | Tier required |
|---|---|
| Most reads/writes (`users`, `posts`, `timelines`) | OAuth 1.0a (consumer + access token/secret) **+** bearer token |
| Media upload, trends | OAuth 1.0a |
| Bookmarks | OAuth 2.0 user-context token (`bookmark.read`/`users.read` scopes) |

Ask for a bookmark without an OAuth2 token and you get a precise `AuthenticationError` naming the missing token and its env var — not a 401 ten frames deep in `requests`.

### Rate limiting that fails before the API does

Every write/engagement call runs through a `RateLimiter` that mirrors X's documented ceilings as a fixed-window counter, so you hit `RateLimitExceeded` locally instead of spending a request to learn you're throttled:

| Bucket | Limit | Window |
|---|---|---|
| `post_actions` | 300 | 15 min |
| `dm_actions` | 1000 | 15 min |
| `follow_actions` | 400 | 24 h |
| `like_actions` | 1000 | 24 h |

```python
from xpal import RateLimiter, RateLimitExceeded
from datetime import timedelta

# Tighten or loosen any bucket — or point it at your own store
limiter = RateLimiter(limits={"post_actions": {"limit": 5, "window": timedelta(minutes=1)}})
x = xpal.client(rate_limiter=limiter)

try:
    x.posts.create(text="...")
except RateLimitExceeded as e:
    print(f"{e.action_type} resets at {e.reset_at}")
```

`check()` is side-effect-free (it never increments); `consume()` counts and raises in one step. The in-memory implementation is the default — swap it for a Redis-backed limiter in a multi-process deployment.

## Why xpal

Tweepy is an excellent, faithful binding to the X API. But "faithful" means you live with the API's seams: two client objects for two API versions, OAuth 1.0a *and* OAuth 2.0 *and* app-only bearer depending on the endpoint, `os.environ` plumbing, raw response objects, and no opinion on rate limiting. xpal is the thin, opinionated layer that smooths those over and gets out of the way.

> Keep the call site boring. Let Tweepy do the protocol. Own credential flow, session lifecycle, and rate-limit accounting once — not at every call.

It's deliberately small: a `client.py` that resolves creds and lazily builds sessions, five domain modules that are mostly one-liners over Tweepy, a rate limiter, and an exception hierarchy. The whole point is that you could read all of it in ten minutes.

### A CLI that mirrors the library

The MCP entry point doubles as a full CLI. There's no hand-written command per method — `xpal <namespace> <method>` reflects straight onto the library, coercing argument types from each method's signature and printing the result as JSON:

```bash
xpal users get_by_username jack
xpal posts create "hello world"
xpal posts create "with media + tags" --media_paths ./cat.jpg --tags python --tags x
xpal timelines search "from:jack" --product Latest --count 20
xpal posts delete 1700000000000000000
```

Positional tokens fill positional params in order; `--flag value` fills keyword params, and **repeating a flag builds a list** (`--tags a --tags b`). `int`/`bool`/`list` params are converted automatically. Run `xpal` with no args (or `xpal --help`) to print every namespace and its methods. Credentials come from the same env vars the library uses. Errors print as a clean one-liner (no traceback) and exit non-zero.

Any `user_id` argument defaults to the **`X_USER_ID`** env var when omitted, so `xpal users get_followers` acts on "you" (an explicit id still wins; `target_user_id` for follow/unfollow is never defaulted). Full reference: [CLI.md](./CLI.md).

```bash
xpal mcp           # start the stdio MCP server through the same binary
```

## What makes xpal different

### A domain-grouped surface, not a flat client

Instead of `client.get_users_followers(...)`, `client.search_recent_tweets(...)`, `client.create_tweet(...)` hanging off one giant object, related operations live together: `x.users.*`, `x.posts.*`, `x.timelines.*`, `x.bookmarks.*`. Discoverable by autocomplete, and "posts" instead of "tweets" throughout.

### Bookmarks done right

Bookmarks are the one surface Tweepy's v2 client can't fully serve, because the endpoint demands an OAuth 2.0 *user-context* token (app-only bearer and OAuth 1.0a both get rejected). xpal carries a small `requests`-based path for exactly this — including a paginated `remove_all()` that deletes bookmarks one-by-one (there's no bulk-delete endpoint) while respecting the rate limiter at every step.

> `remove_all()` is **destructive and irreversible**. The MCP tool wrapping it is tagged so AI clients prompt for explicit confirmation.

### MCP server — drive X with an AI

The same library doubles as a [Model Context Protocol](https://modelcontextprotocol.io) server over **stdio** — the transport local MCP clients expect. Every domain method is exposed as an MCP tool, built on [FastMCP](https://github.com/jlowin/fastmcp).

```bash
xpal mcp            # stdio MCP server, bundled with the package
```

Wire it into Claude Desktop, Cursor, Zed, Continue, Goose, or anything that speaks MCP:

```json
{
  "mcpServers": {
    "xpal": {
      "command": "xpal",
      "args": ["mcp"],
      "env": {
        "X_CONSUMER_KEY": "...",
        "X_CONSUMER_KEY_SECRET": "...",
        "X_ACCESS_TOKEN": "...",
        "X_ACCESS_TOKEN_SECRET": "...",
        "X_BEARER_TOKEN": "...",
        "X_AUTH2_ACCESS_TOKEN": "..."
      }
    }
  }
}
```

`X_AUTH2_ACCESS_TOKEN` (the OAuth 2.0 user-context token) is only needed for the **bookmark** tools — every other tool works with the five OAuth 1.0a + bearer vars above. The server also reads a `.env` file via `python-dotenv`, so you can omit the `env` block and keep credentials there instead.

Then ask your model in plain English:

> *"Find the three most-engaged replies to @jack's latest post and draft a thoughtful response to each."*

The destructive `delete_all_bookmarks` tool is described so the client renders a confirmation prompt before it fires.

> **Note:** it's a **stdio** server. To expose it over the network you'd add an entry point that calls `server.run(transport="http", host=..., port=...)`; the default `server.run()` is stdio.

## Architecture

```
your code ──┐
            ├──►  xpal.client()  ──►  XClient ──►  Tweepy v2 (tweepy.Client)  ──►  X API
AI client ──┘         │                  │     ├─►  Tweepy v1.1 (tweepy.API)  ──►  (media, trends)
 (MCP/stdio)          │                  │     └─►  requests (OAuth2)         ──►  (bookmarks)
                      │                  │
                 RateLimiter        users · posts · timelines · bookmarks
```

One `XClient` holds the credentials, the lazily-built sessions, and the rate limiter. The five domain modules are thin facades that translate friendly calls into Tweepy invocations and normalize responses to plain dicts. The MCP server (`src/xpal/mcp.py`) is a stateless adapter — every tool is a one-liner delegating to a shared lazy client.

## API

### `xpal.client(**creds, rate_limiter=None) -> XClient`

Factory. All credential params are optional and fall back to the environment. Returns an `XClient` exposing the five namespaces below.

### `x.users`

| Method | Returns | Notes |
|---|---|---|
| `me()` | `dict \| None` | The authenticated account (resolves "your" id). |
| `get_by_id(user_id)` | `dict \| None` | Profile by numeric id. |
| `get_by_username(screen_name)` | `dict \| None` | Profile by handle. |
| `lookup(ids=None, usernames=None)` | `list[dict]` | Batch up to 100; pass exactly one of `ids`/`usernames`. |
| `get_followers(user_id, count=100, cursor=None)` | `list[dict]` | Paginated; `cursor` is the next-page token. |
| `get_following(user_id, count=100, cursor=None)` | `list[dict]` | Paginated. |
| `posts(user_id, count=100, cursor=None)` | `list[dict]` | A user's recent posts, with `public_metrics`. |
| `follow(target_user_id)` / `unfollow(target_user_id)` | `dict` | `{"user_id", "following"}`. |

### `x.posts`

| Method | Returns | Notes |
|---|---|---|
| `create(text, media_paths=None, reply_to=None, quote_to=None, community_id=None, tags=None)` | `dict \| None` | `media_paths` upload via v1.1; `tags` appended as `#hashtags`. `quote_to` quotes a post; `community_id` posts into a Community (post-only — no read endpoint exists). **`reply_to` only works if the original post @mentions you or is a reply to your post** — X blocks arbitrary API replies as anti-spam. |
| `quote(post_id, text, media_paths=None, tags=None)` | `dict \| None` | Convenience wrapper over `create(quote_to=...)`. |
| `repost(post_id)` / `unrepost(post_id)` | `dict` | Retweet / undo. `{"post_id", "reposted"}`. |
| `get(post_id)` | `dict \| None` | Single post incl. `public_metrics` (like/reply/repost/quote counts). |
| `replies(post_id, count=100, cursor=None)` | `list[dict]` | Conversation replies via `conversation_id` search (~7-day window). |
| `likers(post_id, count=100, cursor=None)` | `list[dict]` | Users who liked the post. |
| `reposters(post_id, count=100, cursor=None)` | `list[dict]` | Users who reposted the post. |
| `delete(post_id)` | `dict` | `{"id", "deleted"}`. |
| `like(post_id)` / `unlike(post_id)` | `dict` | `{"post_id", "liked"}`. |
| `create_poll(text, choices, duration_minutes)` | `dict \| None` | 2–4 choices; 5–10080 min. |

### `x.timelines`

| Method | Returns | Notes |
|---|---|---|
| `home(count=100, cursor=None)` | `list[dict]` | Algorithmic "For You". |
| `following(count=100)` | `list[dict]` | Reverse-chronological, replies/retweets excluded. |
| `list_posts(list_id, count=100, cursor=None)` | `list[dict]` | A curated List's timeline, with `public_metrics`. |
| `search(query, product="Top", count=100, cursor=None)` | `list[dict]` | `product` `"Top"`→relevancy, else recency. `count` clamped 10–100. |
| `mentions(user_id, count=100, cursor=None)` | `list[dict]` | Posts mentioning a user. |
| `trends(category=None, count=50)` | `list[dict]` | v1.1 worldwide (WOEID 1); optional local category filter. |

### `x.bookmarks`

Requires an OAuth 2.0 user-context token.

| Method | Returns | Notes |
|---|---|---|
| `list(count=100, cursor=None)` | `list[dict]` | `count` clamped 1–100. Basic tier+. |
| `add(post_id, folder_id=None)` | `dict` | `folder_id` accepted but ignored (Tweepy v2 gap). |
| `remove(post_id)` | `dict` | |
| `remove_all()` | `dict` | **Destructive.** Paginates + deletes one-by-one; `{"deleted_count"}`. |

### `x.dms`

| Method | Returns | Notes |
|---|---|---|
| `send(participant_id, text, media_id=None)` | `dict` | Send a 1:1 direct message. |
| `list(participant_id=None, count=100, cursor=None)` | `list[dict]` | Read DM events. **Requires the `dm.read` scope, which X gates separately** — confirm your access tier grants it. Omit `participant_id` for all conversations. |

> [!NOTE]
> **Communities are post-only.** You can publish into a Community via `posts.create(..., community_id=...)`, but the X API v2 exposes **no endpoint to read a Community timeline**, so there is no `timelines.community(...)`. Use a List or search as a workaround.

### Exceptions

```
XPalError                     # base — catch this to catch everything
├── AuthenticationError       # missing/invalid creds; message names the absent token + env var
├── XApiError                 # X API returned an error; clean one-line message + .status_code
└── RateLimitExceeded         # .action_type, .reset_at
```

### `RateLimiter(limits=None)`

`check(action_type) -> bool` (pure) · `consume(action_type) -> None` (counts, raises) · `reset(action_type=None)`.

## Configuration

Credentials resolve **explicit kwarg > `TWITTER_*` > `X_*`**. Provide whichever set you already have.

| Client param | `TWITTER_*` env | `X_*` env | Needed for |
|---|---|---|---|
| `api_key` | `TWITTER_API_KEY` | `X_CONSUMER_KEY` | everything |
| `api_secret` | `TWITTER_API_SECRET` | `X_CONSUMER_KEY_SECRET` | everything |
| `access_token` | `TWITTER_ACCESS_TOKEN` | `X_ACCESS_TOKEN` | everything |
| `access_token_secret` | `TWITTER_ACCESS_TOKEN_SECRET` | `X_ACCESS_TOKEN_SECRET` | everything |
| `bearer_token` | `TWITTER_BEARER_TOKEN` | `X_BEARER_TOKEN` | v2 reads/writes |
| `oauth2_access_token` | `TWITTER_OAUTH2_USER_ACCESS_TOKEN` | `X_AUTH2_ACCESS_TOKEN` | bookmarks |

A `.env` file is honored by the MCP server (via `python-dotenv`); for the library, load it yourself or set the vars in your shell.

## Development

```bash
pip install -e ".[dev]"
python -c "import xpal; from xpal import mcp; print('ok', mcp.server.name)"   # smoke test
pytest                                                                        # test suite
```

## Project layout

```
.
├── README.md
├── LICENSE
├── pyproject.toml          # package metadata + `xpal` console script
└── src/xpal/
    ├── __init__.py         # xpal.client() factory + public re-exports
    ├── client.py           # XClient: credential resolution, lazy v1/v2/OAuth2 sessions
    ├── users.py            # x.users
    ├── posts.py            # x.posts
    ├── timelines.py        # x.timelines
    ├── bookmarks.py        # x.bookmarks (OAuth2 path)
    ├── dms.py              # x.dms (dm.read scope for reads)
    ├── rate_limiter.py     # fixed-window RateLimiter
    ├── exceptions.py       # XPalError hierarchy
    └── mcp.py              # stdio MCP server + reflection CLI — thin adapter
```

## License

[MIT](./LICENSE) © 2026 Ran Aroussi
