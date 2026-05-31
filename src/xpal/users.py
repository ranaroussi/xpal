"""User operations for xpal."""

from typing import Optional


class Users:
    """User lookups, followers, and following. Access via ``xp.users``."""

    def __init__(self, client):
        self._client = client

    def get_by_id(self, user_id: str) -> dict | None:
        """Fetch a user by ID.

        Returns user data dict or None if not found.
        """
        user = self._client.v2.get_user(
            id=user_id,
            user_fields=["id", "name", "username", "profile_image_url", "description"],
        )
        return user.data.data if user.data else None

    def get_by_username(self, screen_name: str) -> dict | None:
        """Fetch a user by screen name / username.

        Returns user data dict or None if not found.
        """
        user = self._client.v2.get_user(
            username=screen_name,
            user_fields=["id", "name", "username", "profile_image_url", "description"],
        )
        return user.data.data if user.data else None

    def me(self) -> dict | None:
        """Return the authenticated user's own profile.

        Useful for resolving "your" user id (e.g. for timeline reconciliation).
        """
        user = self._client.v2.get_me(
            user_fields=["id", "name", "username", "profile_image_url", "description"],
        )
        return user.data.data if user.data else None

    def lookup(
        self,
        ids: Optional[list[str]] = None,
        usernames: Optional[list[str]] = None,
    ) -> list[dict]:
        """Batch-fetch up to 100 users by ID or username in one request.

        Pass exactly one of ``ids`` or ``usernames``.

        Args:
            ids: Up to 100 numeric user IDs.
            usernames: Up to 100 handles (without '@').
        """
        if bool(ids) == bool(usernames):
            raise ValueError("Pass exactly one of 'ids' or 'usernames'.")
        users = self._client.v2.get_users(
            ids=ids,
            usernames=usernames,
            user_fields=["id", "name", "username", "profile_image_url", "description"],
        )
        return [u.data for u in (users.data or [])]

    def follow(self, target_user_id: str) -> dict:
        """Follow a user.

        Args:
            target_user_id: The ID of the user to follow.
        """
        self._client.rate_limiter.consume("follow_actions")
        result = self._client.v2.follow_user(target_user_id=target_user_id)
        return {"user_id": target_user_id, "following": result.data["following"]}

    def unfollow(self, target_user_id: str) -> dict:
        """Unfollow a user.

        Args:
            target_user_id: The ID of the user to unfollow.
        """
        self._client.rate_limiter.consume("follow_actions")
        result = self._client.v2.unfollow_user(target_user_id=target_user_id)
        return {"user_id": target_user_id, "following": result.data["following"]}

    def posts(
        self,
        user_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> list[dict]:
        """Fetch a user's recent posts (their timeline).

        Includes ``public_metrics``. This is the real ``get_users_tweets``
        endpoint — handy for outcome reconciliation (pulling your own recent
        posts/replies).

        Args:
            user_id: The user ID whose posts to retrieve.
            count: Results per page (5-100). Default 100.
            cursor: Pagination token for the next page.
        """
        tweets = self._client.v2.get_users_tweets(
            id=user_id,
            max_results=count,
            pagination_token=cursor,
            tweet_fields=["id", "text", "created_at", "author_id", "public_metrics"],
        )
        return [t.data for t in (tweets.data or [])]

    def get_followers(
        self,
        user_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> list[dict]:
        """Retrieve followers for a given user.

        Args:
            user_id: The user ID whose followers to retrieve.
            count: Results per page (max 100). Default 100.
            cursor: Pagination token for next page.
        """
        self._client.rate_limiter.consume("follow_actions")
        followers = self._client.v2.get_users_followers(
            id=user_id,
            max_results=count,
            pagination_token=cursor,
            user_fields=["id", "name", "username"],
        )
        return [u.data for u in (followers.data or [])]

    def get_following(
        self,
        user_id: str,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> list[dict]:
        """Retrieve users the given user is following.

        Args:
            user_id: The user ID whose following list to retrieve.
            count: Results per page (max 100). Default 100.
            cursor: Pagination token for next page.
        """
        self._client.rate_limiter.consume("follow_actions")
        following = self._client.v2.get_users_following(
            id=user_id,
            max_results=count,
            pagination_token=cursor,
            user_fields=["id", "name", "username"],
        )
        return [u.data for u in (following.data or [])]
