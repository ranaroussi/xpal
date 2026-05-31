"""Post operations for xpal (create, delete, like, polls).

Uses "posts" instead of "tweets" per project convention.
"""

import os
from typing import Optional

from .pagination import Page, page, TWEET_FIELDS, TWEET_EXPANSIONS, MEDIA_FIELDS, USER_FIELDS, normalize_includes

_VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
_GIF_EXTS = {".gif"}


class Posts:
    """Post CRUD, likes, and polls. Access via ``xp.posts``."""

    def __init__(self, client):
        self._client = client

    def _upload_media(self, path: str, alt_text: Optional[str] = None) -> str:
        """Upload one media file (image/gif/video) and return its media id.

        Videos and GIFs use chunked upload with the right ``media_category``.
        Alt text, when given, is attached via v1.1 media metadata.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext in _VIDEO_EXTS:
            media = self._client.v1.media_upload(
                filename=path, chunked=True, media_category="tweet_video"
            )
        elif ext in _GIF_EXTS:
            media = self._client.v1.media_upload(
                filename=path, chunked=True, media_category="tweet_gif"
            )
        else:
            media = self._client.v1.media_upload(filename=path)
        if alt_text:
            self._client.v1.create_media_metadata(media.media_id_string, alt_text)
        return media.media_id_string

    def create(
        self,
        text: str,
        media_paths: Optional[list[str]] = None,
        media_alt_texts: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
        quote_to: Optional[str] = None,
        community_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict | None:
        """Create a new post.

        Args:
            text: Post text content (max 280 characters).
            media_paths: Local file paths to media for upload and attachment.
                Images, GIFs (``.gif``), and videos (``.mp4``/``.mov``/``.m4v``)
                are detected by extension; GIFs/videos use chunked upload.
            media_alt_texts: Accessibility alt text, positionally aligned with
                ``media_paths`` (use ``None``/``""`` to skip an item).
            reply_to: Post ID to reply to. Note: X restricts API replies to
                conversations you're part of — the original post must @mention
                you, or be a reply to one of your posts. Otherwise it fails.
            quote_to: Post ID to quote (attaches the quoted post as a card).
            community_id: Post into a Community by its ID. (Reading a community
                timeline has no X API v2 endpoint — posting only.)
            tags: Hashtags to append (without '#').
        """
        self._client.rate_limiter.consume("post_actions")
        tweet_data: dict = {"text": text}
        if reply_to:
            tweet_data["in_reply_to_tweet_id"] = reply_to
        if quote_to:
            tweet_data["quote_tweet_id"] = quote_to
        if community_id:
            tweet_data["community_id"] = community_id
        if tags:
            tweet_data["text"] += " " + " ".join(f"#{tag}" for tag in tags)
        if media_paths:
            alts = media_alt_texts or []
            media_ids = [
                self._upload_media(path, alts[i] if i < len(alts) else None)
                for i, path in enumerate(media_paths)
            ]
            tweet_data["media_ids"] = media_ids
        tweet = self._client.v2.create_tweet(**tweet_data)
        if not tweet.data:
            return None
        return tweet.data

    def quote(
        self,
        post_id: str,
        text: str,
        media_paths: Optional[list[str]] = None,
        media_alt_texts: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> dict | None:
        """Quote a post — recontextualize it to your own audience.

        Args:
            post_id: The ID of the post to quote.
            text: Your commentary (max 280 characters).
            media_paths: Local file paths to media for upload and attachment.
            media_alt_texts: Alt text aligned with ``media_paths``.
            tags: Hashtags to append (without '#').
        """
        return self.create(
            text=text, quote_to=post_id, media_paths=media_paths,
            media_alt_texts=media_alt_texts, tags=tags,
        )

    def repost(self, post_id: str) -> dict:
        """Repost (retweet) a post.

        Args:
            post_id: The ID of the post to repost.
        """
        self._client.rate_limiter.consume("post_actions")
        result = self._client.v2.retweet(tweet_id=post_id)
        return {"post_id": post_id, "reposted": result.data["retweeted"]}

    def unrepost(self, post_id: str) -> dict:
        """Remove a repost (undo a retweet).

        Args:
            post_id: The ID of the post to un-repost.
        """
        self._client.rate_limiter.consume("post_actions")
        result = self._client.v2.unretweet(source_tweet_id=post_id)
        return {"post_id": post_id, "reposted": result.data["retweeted"]}

    def delete(self, post_id: str) -> dict:
        """Delete a post by ID.

        Args:
            post_id: The ID of the post to delete.
        """
        self._client.rate_limiter.consume("post_actions")
        result = self._client.v2.delete_tweet(id=post_id)
        return {"id": post_id, "deleted": result.data["deleted"]}

    def get(self, post_id: str) -> dict | None:
        """Get detailed information about a specific post.

        Includes ``public_metrics`` (like / reply / repost / quote counts) and
        expansion objects (author, media, referenced posts) under an
        ``includes`` key when present.

        Args:
            post_id: The ID of the post to fetch.
        """
        tweet = self._client.v2.get_tweet(
            id=post_id,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        )
        if not tweet.data:
            return None
        data = dict(tweet.data.data)
        includes = normalize_includes(getattr(tweet, "includes", None))
        if includes:
            data["includes"] = includes
        return data

    def get_many(self, post_ids: list[str]) -> Page:
        """Batch-fetch up to 100 posts by ID in one request.

        Args:
            post_ids: List of post IDs (max 100).

        Returns:
            A :class:`Page` of posts; ``.includes`` carries authors/media.
        """
        return page(self._client.v2.get_tweets(
            ids=post_ids,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))

    def replies(
        self,
        post_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Fetch replies to a post (its conversation), for saturation analysis.

        Implemented via recent search on ``conversation_id`` — so it is bound
        by the search window (roughly the last 7 days).

        Args:
            post_id: The ID of the post whose replies to retrieve.
            count: Results per page (10-100). Default 100.
            cursor: Pagination token (next_token) for the next page.
        """
        effective_count = 10 if (count or 0) < 10 else min(count, 100)
        return page(self._client.v2.search_recent_tweets(
            query=f"conversation_id:{post_id}",
            max_results=effective_count,
            next_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))

    def quotes(
        self,
        post_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Retrieve posts that quote a given post.

        Args:
            post_id: The ID of the quoted post.
            count: Results per page (10-100). Default 100.
            cursor: Pagination token for the next page.
        """
        effective_count = 10 if (count or 0) < 10 else min(count, 100)
        return page(self._client.v2.get_quote_tweets(
            id=post_id,
            max_results=effective_count,
            pagination_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))

    def likers(
        self,
        post_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Retrieve users who liked a post.

        Args:
            post_id: The ID of the post.
            count: Results per page (max 100). Default 100.
            cursor: Pagination token for the next page.
        """
        return page(self._client.v2.get_liking_users(
            id=post_id,
            max_results=count,
            pagination_token=cursor,
            user_fields=USER_FIELDS,
            user_auth=True,
        ))

    def reposters(
        self,
        post_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Retrieve users who reposted (retweeted) a post.

        Args:
            post_id: The ID of the post.
            count: Results per page (max 100). Default 100.
            cursor: Pagination token for the next page.
        """
        return page(self._client.v2.get_retweeters(
            id=post_id,
            max_results=count,
            pagination_token=cursor,
            user_fields=USER_FIELDS,
            user_auth=True,
        ))

    def like(self, post_id: str) -> dict:
        """Like a post.

        Args:
            post_id: The ID of the post to like.
        """
        self._client.rate_limiter.consume("like_actions")
        result = self._client.v2.like(tweet_id=post_id)
        return {"post_id": post_id, "liked": result.data["liked"]}

    def unlike(self, post_id: str) -> dict:
        """Unlike a post.

        Args:
            post_id: The ID of the post to unlike.
        """
        self._client.rate_limiter.consume("like_actions")
        result = self._client.v2.unlike(tweet_id=post_id)
        return {"post_id": post_id, "liked": not result.data["liked"]}

    def create_poll(
        self,
        text: str,
        choices: list[str],
        duration_minutes: int,
    ) -> dict | None:
        """Create a post with a poll.

        Args:
            text: The question or text for the poll.
            choices: Poll choices (2-4, each max 25 characters).
            duration_minutes: Duration in minutes (min 5, max 10080 / 7 days).
        """
        self._client.rate_limiter.consume("post_actions")
        tweet = self._client.v2.create_tweet(
            text=text,
            poll_options=choices,
            poll_duration_minutes=duration_minutes,
        )
        if not tweet.data:
            return None
        return tweet.data
