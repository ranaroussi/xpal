"""Timeline and search operations for xpal."""

import logging
from typing import Optional

from .pagination import Page, page, TWEET_FIELDS, TWEET_EXPANSIONS, MEDIA_FIELDS, USER_FIELDS

logger = logging.getLogger(__name__)


class Timelines:
    """Home timeline, lists, search, trends, and mentions. Access via ``xp.timelines``."""

    def __init__(self, client):
        self._client = client

    def home(
        self,
        count: Optional[int] = 100,
        seen_post_ids: Optional[list[str]] = None,
        cursor: Optional[str] = None,
    ) -> Page:
        """Get posts from your home timeline (For You / algorithmic).

        Args:
            count: Number of posts to retrieve (5-100). Default 100.
            seen_post_ids: Post IDs already seen (reserved for future use).
            cursor: Pagination token for next page.

        Returns:
            A :class:`Page` of posts (use ``.next_cursor`` / ``.includes``).
        """
        return page(self._client.v2.get_home_timeline(
            max_results=count,
            pagination_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))

    def following(
        self,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Get posts from accounts you follow (reverse chronological).

        Args:
            count: Number of posts to retrieve (5-100). Default 100.
            cursor: Pagination token for next page.
        """
        return page(self._client.v2.get_home_timeline(
            max_results=count,
            pagination_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
            exclude=["replies", "retweets"],
        ))

    def list_posts(
        self,
        list_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Get posts from a specific List's timeline.

        A clean chronological feed of accounts on a curated List — ideal for
        topical source lists and velocity tracking.

        Args:
            list_id: The ID of the List.
            count: Results per page (max 100). Default 100.
            cursor: Pagination token for the next page.
        """
        return page(self._client.v2.get_list_tweets(
            id=list_id,
            max_results=count,
            pagination_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))

    def search(
        self,
        query: str,
        product: Optional[str] = "Top",
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Search for recent posts (last ~7 days).

        Args:
            query: Search query (supports operators like #hashtag, from:user).
            product: Sort preference — 'Top' (relevancy) or 'Latest' (recency).
            count: Results per page (10-100). Default 100.
            cursor: Pagination token (next_token) for next page.
        """
        sort_order = "relevancy" if product == "Top" else "recency"

        if count is None:
            effective_count = 100
        elif count < 10:
            logger.info(f"Requested count {count} < minimum 10; using 10.")
            effective_count = 10
        elif count > 100:
            logger.info(f"Requested count {count} > maximum 100; using 100.")
            effective_count = 100
        else:
            effective_count = count

        return page(self._client.v2.search_recent_tweets(
            query=query,
            max_results=effective_count,
            sort_order=sort_order,
            next_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))

    def trends(
        self,
        category: Optional[str] = None,
        count: Optional[int] = 50,
    ) -> Page:
        """Retrieve trending topics.

        Uses X API v1.1 (v2 trends require specific WOEID). No pagination.

        Args:
            category: Filter by category (e.g. 'Sports', 'News'). Best-effort.
            count: Number of trends to return. Default 50, max 50.
        """
        trends_data = self._client.v1.get_place_trends(id=1)  # WOEID 1 = Worldwide
        trends_list = trends_data[0]["trends"]
        if category:
            trends_list = [t for t in trends_list if t.get("category") == category]
        return Page(trends_list[:count or 50])

    def mentions(
        self,
        user_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Get posts mentioning a specific user.

        Args:
            user_id: The user ID whose mentions to retrieve.
            count: Number of mentions (5-100). Default 100.
            cursor: Pagination token for next page.
        """
        return page(self._client.v2.get_users_mentions(
            id=user_id,
            max_results=count,
            pagination_token=cursor,
            tweet_fields=TWEET_FIELDS,
            expansions=TWEET_EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            user_fields=USER_FIELDS,
        ))
