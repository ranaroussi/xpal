"""Bookmark operations for xpal.

These endpoints require OAuth 2.0 User Context (PKCE authorization flow
with bookmark.read, bookmark.write, and users.read scopes).
"""

from typing import Optional

from .pagination import Page


class Bookmarks:
    """Bookmark CRUD. Access via ``xp.bookmarks``."""

    def __init__(self, client):
        self._client = client

    def list(
        self,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> Page:
        """Retrieve the authenticated user's bookmarked posts.

        Requires Basic access tier or higher and OAuth 2.0 user token.

        Args:
            count: Results per page (1-100). Default 100.
            cursor: Pagination token for next page.

        Returns:
            A :class:`Page` of posts (use ``.next_cursor`` for the next page).
        """
        if count is None:
            effective_count = 100
        elif count < 1:
            effective_count = 1
        elif count > 100:
            effective_count = 100
        else:
            effective_count = count

        headers, user_id = self._client._get_oauth2_headers_and_user_id()
        params: dict = {
            "max_results": effective_count,
            "tweet.fields": "id,text,created_at,author_id",
        }
        if cursor:
            params["pagination_token"] = cursor

        data = self._client._bookmarks_request("GET", headers, user_id, params=params)
        next_cursor = data.get("meta", {}).get("next_token")
        return Page(data.get("data", []), next_cursor=next_cursor)

    def add(self, post_id: str, folder_id: Optional[str] = None) -> dict:
        """Bookmark a post.

        Args:
            post_id: The ID of the post to bookmark.
            folder_id: Bookmark folder ID (currently unsupported by tweepy v2, ignored).
        """
        self._client.rate_limiter.consume("post_actions")
        result = self._client.v2.bookmark(tweet_id=post_id)
        return {"post_id": post_id, "bookmarked": result.data["bookmarked"]}

    def remove(self, post_id: str) -> dict:
        """Remove a post from bookmarks.

        Args:
            post_id: The ID of the post to remove.
        """
        self._client.rate_limiter.consume("post_actions")
        result = self._client.v2.remove_bookmark(tweet_id=post_id)
        return {"post_id": post_id, "bookmarked": not result.data["bookmarked"]}

    def remove_all(self) -> dict:
        """Permanently delete ALL bookmarks, one by one.

        **Destructive and irreversible.** Always confirm with the user
        before calling this method.

        X API v2 has no bulk-delete endpoint, so bookmarks are
        fetched page-by-page and removed individually. Both operations
        require OAuth 2.0.
        """
        headers, user_id = self._client._get_oauth2_headers_and_user_id()
        deleted = 0
        next_token = None

        while True:
            params: dict = {"max_results": 100}
            if next_token:
                params["pagination_token"] = next_token
            data = self._client._bookmarks_request("GET", headers, user_id, params=params)
            posts = data.get("data", [])
            if not posts:
                break
            for post in posts:
                self._client.rate_limiter.consume("post_actions")
                self._client._bookmarks_request("DELETE", headers, user_id, tweet_id=post["id"])
                deleted += 1
            next_token = data.get("meta", {}).get("next_token")
            if not next_token:
                break

        return {"status": "all bookmarks deleted", "deleted_count": deleted}
