"""Direct message operations for xpal.

Reading DMs (``list``) requires the ``dm.read`` scope, which X gates
separately from the standard scopes — confirm your access tier grants it
before relying on this surface.
"""

from typing import Optional


class Dms:
    """Direct messages. Access via ``xp.dms``."""

    def __init__(self, client):
        self._client = client

    def send(
        self,
        participant_id: str,
        text: str,
        media_id: Optional[str] = None,
    ) -> dict:
        """Send a direct message to a user.

        Args:
            participant_id: The recipient's user ID.
            text: The message text.
            media_id: Optional uploaded media id to attach.
        """
        self._client.rate_limiter.consume("dm_actions")
        result = self._client.v2.create_direct_message(
            participant_id=participant_id,
            text=text,
            media_id=media_id,
        )
        return result.data

    def list(
        self,
        participant_id: Optional[str] = None,
        count: Optional[int] = 100,
        cursor: Optional[str] = None,
    ) -> list[dict]:
        """Read direct message events.

        Requires the ``dm.read`` scope (separately gated by X).

        Args:
            participant_id: Limit to the 1:1 conversation with this user.
                If omitted, returns events across all conversations.
            count: Results per page (max 100). Default 100.
            cursor: Pagination token for the next page.
        """
        params: dict = {
            "max_results": count,
            "dm_event_fields": ["id", "text", "created_at", "sender_id", "dm_conversation_id"],
        }
        if cursor:
            params["pagination_token"] = cursor

        if participant_id:
            events = self._client.v2.get_direct_message_events(
                participant_id=participant_id, **params
            )
        else:
            events = self._client.v2.get_direct_message_events(**params)
        return [e.data for e in (events.data or [])]
