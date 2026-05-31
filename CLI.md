# xpal CLI

The `xpal` command is installed with the package (`pip install xpal`). It reflects
directly onto the library, so every namespace method is callable from the shell.

```
xpal                                  # print help (all namespaces + methods)
xpal --help                           # same as above
xpal --version                        # print the installed version (also -V)
xpal mcp                              # start the stdio MCP server
xpal <namespace> <method> [args] [--flags]
```

## How arguments map

- **Positional tokens** fill the method's positional parameters, in order.
- **`--flag value`** fills a parameter by name (works for positional or keyword params).
- **Repeat a flag to build a list**: `--tags python --tags x` → `["python", "x"]`.
- Each `--flag` takes exactly one value; repeat the flag to pass multiple.
- Types are coerced from each method's signature: `int` and `list` are converted
  automatically, `bool` is truthy for `1`/`true`/`yes`/`y` (anything else is false),
  and everything else is passed as a string.
- Output is printed as JSON. Paginated commands print `{"data": [...], "next_cursor": ..., "includes": ...}` (the `next_cursor`/`includes` keys are omitted when empty); pass `next_cursor` back via `--cursor` to fetch the next page.

### Default `user_id` via `X_USER_ID`

Any command whose parameter is named `user_id` (e.g. `users get_by_id`,
`users get_followers`, `users get_following`, `users posts`,
`timelines mentions`) falls back to the **`X_USER_ID`** environment variable when
you don't pass one — so `xpal users get_followers` acts on "you". If the argument
is omitted *and* `X_USER_ID` is unset, the command errors. An explicit argument
always wins. This does **not** apply to `target_user_id` (follow/unfollow), which
must be given explicitly.

```bash
export X_USER_ID=3066611
xpal users get_followers          # → followers of X_USER_ID
xpal users posts --count 5        # → your recent posts
xpal users get_followers 783214   # explicit id overrides the env default
```

Credentials are read from the same environment variables as the library
(`TWITTER_*` or `X_*`; a `.env` file is auto-loaded). See the
[Configuration](./README.md#configuration) table for the full list.

---

## `users`

| Command | Parameters |
|---|---|
| `xpal users me` | — |
| `xpal users get_by_id <user_id>` | `user_id` |
| `xpal users get_by_username <screen_name>` | `screen_name` |
| `xpal users lookup --ids <id> [--ids ...]` / `--usernames <name> [...]` | `ids` *or* `usernames` (exactly one; up to 100) |
| `xpal users get_followers <user_id> [--count 100] [--cursor <token>]` | `user_id`, `count`, `cursor` |
| `xpal users get_following <user_id> [--count 100] [--cursor <token>]` | `user_id`, `count`, `cursor` |
| `xpal users posts <user_id> [--count 100] [--cursor <token>]` | `user_id`, `count`, `cursor` |
| `xpal users follow <target_user_id>` | `target_user_id` |
| `xpal users unfollow <target_user_id>` | `target_user_id` |
| `xpal users mute <target_user_id>` | `target_user_id` |
| `xpal users unmute <target_user_id>` | `target_user_id` |
| `xpal users get_muted [--count 100] [--cursor <token>]` | `count`, `cursor` |
| `xpal users get_blocked [--count 100] [--cursor <token>]` | `count`, `cursor` |

```bash
xpal users me
xpal users get_by_username jack
xpal users lookup --usernames jack --usernames elonmusk
xpal users get_followers 2244994945 --count 50
xpal users posts 2244994945
xpal users follow 2244994945
```

## `posts`

| Command | Parameters |
|---|---|
| `xpal posts create <text> [--media_paths <path>...] [--media_alt_texts <alt>...] [--reply_to <id>] [--quote_to <id>] [--community_id <id>] [--tags <tag>...]` | `text`, `media_paths`, `media_alt_texts`, `reply_to`, `quote_to`, `community_id`, `tags` |
| `xpal posts quote <post_id> <text> [--media_paths <path>...] [--media_alt_texts <alt>...] [--tags <tag>...]` | `post_id`, `text`, `media_paths`, `media_alt_texts`, `tags` |
| `xpal posts repost <post_id>` | `post_id` |
| `xpal posts unrepost <post_id>` | `post_id` |
| `xpal posts get <post_id>` | `post_id` (returns `public_metrics` + `includes`) |
| `xpal posts get_many --post_ids <id>...` | `post_ids` (batch up to 100) |
| `xpal posts replies <post_id> [--count 100] [--cursor <token>]` | `post_id`, `count`, `cursor` |
| `xpal posts quotes <post_id> [--count 100] [--cursor <token>]` | `post_id`, `count`, `cursor` (clamped 10–100) |
| `xpal posts likers <post_id> [--count 100] [--cursor <token>]` | `post_id`, `count`, `cursor` |
| `xpal posts reposters <post_id> [--count 100] [--cursor <token>]` | `post_id`, `count`, `cursor` |
| `xpal posts like <post_id>` | `post_id` |
| `xpal posts unlike <post_id>` | `post_id` |
| `xpal posts delete <post_id>` | `post_id` |
| `xpal posts create_poll <text> --choices <c>... --duration_minutes <n>` | `text`, `choices`, `duration_minutes` |

```bash
xpal posts create "hello world"
xpal posts create "with media + tags" --media_paths ./cat.jpg --tags python --tags x
xpal posts quote 1700000000000000000 "great take"
xpal posts repost 1700000000000000000
xpal posts get 1700000000000000000
xpal posts replies 1700000000000000000 --count 50
xpal posts create_poll "Tabs or spaces?" --choices Tabs --choices Spaces --duration_minutes 1440
xpal posts delete 1700000000000000000
```

> **Replies** (`--reply_to`) only succeed inside conversations the account is part of
> (X anti-spam rule). **Communities** (`--community_id`) are post-only — there is no
> endpoint to read a community timeline.

## `timelines`

| Command | Parameters |
|---|---|
| `xpal timelines home [--count 100] [--seen_post_ids <id>...] [--cursor <token>]` | `count`, `seen_post_ids`, `cursor` |
| `xpal timelines following [--count 100]` | `count` |
| `xpal timelines list_posts <list_id> [--count 100] [--cursor <token>]` | `list_id`, `count`, `cursor` |
| `xpal timelines search <query> [--product Top] [--count 100] [--cursor <token>]` | `query`, `product`, `count`, `cursor` |
| `xpal timelines mentions <user_id> [--count 100] [--cursor <token>]` | `user_id`, `count`, `cursor` |
| `xpal timelines trends [--category <name>] [--count 50]` | `category`, `count` |

```bash
xpal timelines home --count 50
xpal timelines following
xpal timelines list_posts 1234567890
xpal timelines search "from:jack web3" --product Latest --count 20
xpal timelines mentions 2244994945
xpal timelines trends
```

## `bookmarks`

Requires an OAuth 2.0 user-context token (`X_AUTH2_ACCESS_TOKEN` /
`TWITTER_OAUTH2_USER_ACCESS_TOKEN`).

| Command | Parameters |
|---|---|
| `xpal bookmarks list [--count 100] [--cursor <token>]` | `count`, `cursor` |
| `xpal bookmarks add <post_id> [--folder_id <id>]` | `post_id`, `folder_id` |
| `xpal bookmarks remove <post_id>` | `post_id` |
| `xpal bookmarks remove_all` | — (**destructive & irreversible**) |

```bash
xpal bookmarks list --count 100
xpal bookmarks add 1700000000000000000
xpal bookmarks remove 1700000000000000000
xpal bookmarks remove_all
```

## `dms`

Reading DMs requires the separately-gated `dm.read` scope.

| Command | Parameters |
|---|---|
| `xpal dms send <participant_id> <text> [--media_id <id>]` | `participant_id`, `text`, `media_id` |
| `xpal dms list [--participant_id <id>] [--count 100] [--cursor <token>]` | `participant_id`, `count`, `cursor` |

```bash
xpal dms send 2244994945 "hey there"
xpal dms list --participant_id 2244994945
```

---

## MCP server

```bash
xpal mcp           # start the stdio MCP server (same credentials as the CLI)
```

Every command above is also exposed as an MCP tool. See the
[MCP section of the README](./README.md#mcp-server--drive-x-with-an-ai) for client config.
