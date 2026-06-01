# Changelog

Repo: https://github.com/ranaroussi/xpal

Versioning is CalVer (`0.YYYYMMDD.micro`), sourced from the root `.version` file.

## 0.20260601.2

### Added

- `bookmarks.folders(count=100, cursor=None)` — list the authenticated user's bookmark folders (`GET /2/users/{id}/bookmarks/folders`), returning a `Page` of `{id, name}` (MCP: `get_bookmark_folders`; CLI: `xpal bookmarks folders`). X currently caps results at 20.
- `bookmarks.folder(folder_id, count=100, cursor=None)` — list the posts inside a specific bookmark folder (`GET /2/users/{id}/bookmarks/folders/{folder_id}`), returning a paginated `Page` (MCP: `get_bookmarks_by_folder`; CLI: `xpal bookmarks folder <folder_id>`).

## 0.20260601.1

### Added

- **Pagination + expansions everywhere.** List-returning methods now return a `Page` (a `list` subclass) carrying `.next_cursor` (the token for the next page, `None` on the last page) and `.includes` (expansion objects keyed by `users`/`tweets`/`media`). `Page` is exported from the package and stays fully list-compatible.
- `posts.get_many(ids)` — batch-fetch up to 100 posts by ID in one request (MCP: `get_tweets`).
- `posts.quotes(post_id)` — list posts that quote a given post (MCP: `get_quote_tweets`).
- `posts.create`/`posts.quote` gained `media_alt_texts` (accessibility alt text, positionally aligned with `media_paths`) and now detect GIFs (`.gif`) and videos (`.mp4`/`.mov`/`.m4v`) by extension, using chunked upload with the correct media category.
- `users.mute` / `users.unmute` (writes) and `users.get_muted` / `users.get_blocked` (reads), with matching MCP tools `mute_user`/`unmute_user`/`get_muted`/`get_blocked`. (X API v2 has no block/unblock create-delete endpoints, so those are intentionally absent.)
- `posts.get` now surfaces expansion objects (author, media, referenced posts) under an `includes` key when present.
- `XApiError.reset_at`: on HTTP 429, the `x-rate-limit-reset` header is parsed into a `datetime` and included in the error message.
- CLI/MCP `--version` (also `-V`).

### Changed

- `MCP` list tools return an envelope (`{data, next_cursor, includes}`) when pagination/expansion data is present, so MCP clients can paginate; single-object tools are unchanged.
- `_resolve_user_id` (CLI & MCP `X_USER_ID` default) now accepts both `str` and `int`, normalizing to the string id the X API expects (some MCP clients cannot send integers).
- All user lookups and timeline/post reads now request richer field sets (`public_metrics`, author/media expansions).

### Fixed

- Read endpoints no longer consume the write rate-limit budget: `users.get_followers`/`get_following` and `bookmarks.list` no longer decrement `follow_actions`/`post_actions`.

## 0.20260601.0

### Added

- `XApiError` exception (subclass of `XPalError`, with `.status_code`) and central error translation: any Tweepy/HTTP error from the underlying sessions now surfaces as a clean, single-line `XApiError` instead of a raw `tweepy.errors.*` exception.
- CLI & MCP: `user_id` arguments default to the **`X_USER_ID`** environment variable when omitted (errors if both the argument and the env var are absent). An explicit value always overrides it; `target_user_id` (follow/unfollow) is never defaulted.
- User lookups now include `public_metrics`, so `users.me`/`get_by_id`/`get_by_username`/`lookup` (and follower/following lists) expose `followers_count`, `following_count`, `tweet_count`, and `listed_count`.
- `CLI.md`: full command reference for the `xpal` CLI.

### Changed

- CLI errors now print as a clean one-line message (no traceback) and exit non-zero, with a hint when a handle is passed where a numeric id is expected.

### Fixed

- `posts.likers` (and `posts.reposters`) now use OAuth 1.0a user context (`user_auth=True`); the likers endpoint rejects app-only auth and previously raised a 403.

## 0.20260531.0 (initial release)

Initial release of **xpal** — a Python client library, CLI, and stdio MCP server for the X (Twitter) API.

### Library

- `xpal.client()` factory returning an `XClient`; credentials resolve with the precedence **explicit kwarg > `TWITTER_*` env > `X_*` env**, with no module-level globals.
- Lazy, cached dual-version sessions: v2 (`tweepy.Client`) for most calls, v1.1 (`tweepy.API`) only for media upload and trends, plus an OAuth 2.0 user-context session for bookmarks. Each call validates only the credential tier it needs.
- Five domain namespaces:
  - `users`: `me`, `get_by_id`, `get_by_username`, `lookup` (batch up to 100), `get_followers`, `get_following`, `posts`, `follow`, `unfollow`.
  - `posts`: `create` (with `quote_to`, `community_id`, media, tags), `quote`, `repost`, `unrepost`, `get` (incl. `public_metrics`), `replies`, `likers`, `reposters`, `delete`, `like`, `unlike`, `create_poll`.
  - `timelines`: `home`, `following`, `list_posts`, `search`, `mentions`, `trends`.
  - `bookmarks`: `list`, `add`, `remove`, `remove_all`.
  - `dms`: `send`, `list` (read requires the separately-gated `dm.read` scope).
- Built-in fixed-window `RateLimiter` (buckets: `post_actions`, `dm_actions`, `follow_actions`, `like_actions`); `check()` is side-effect-free, `consume()` counts and raises `RateLimitExceeded` locally before hitting the API.
- Typed exception hierarchy: `XPalError` → `AuthenticationError`, `RateLimitExceeded`.

### CLI & MCP

- `xpal mcp` starts a stdio MCP server exposing every namespace method as a tool.
- `xpal <namespace> <method> [args] [--flags]` reflects straight onto the library, coercing argument types from each method's signature and printing JSON.

### Notes & constraints

- No simulated or mock functionality: methods that the X API cannot actually back were removed entirely (former `posts.vote_poll`, `users.get_mutual_followers`, `timelines.highlights`).
- Replies (`posts.create(reply_to=...)`) only succeed inside conversations the account is part of (X anti-spam rule).
- Communities are post-only (`posts.create(community_id=...)`); the X API v2 has no endpoint to read a Community timeline.
