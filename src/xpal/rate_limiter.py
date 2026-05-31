"""In-memory rate limiter for xpal.

Fixed-window counter: each bucket counts actions until its window elapses,
then resets. Pluggable design: swap this for a Redis-backed implementation
in production.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from .exceptions import RateLimitExceeded

# Default rate-limit configuration matching X documented limits.
DEFAULT_RATE_LIMITS: dict[str, dict] = {
    "post_actions": {"limit": 300, "window": timedelta(minutes=15)},
    "dm_actions": {"limit": 1000, "window": timedelta(minutes=15)},
    "follow_actions": {"limit": 400, "window": timedelta(hours=24)},
    "like_actions": {"limit": 1000, "window": timedelta(hours=24)},
}


class _Counter:
    __slots__ = ("count", "reset_time")

    def __init__(self, reset_time: datetime):
        self.count = 0
        self.reset_time = reset_time


class RateLimiter:
    """Fixed-window rate limiter with per-bucket windows.

    Args:
        limits: Mapping of bucket name to {"limit": int, "window": timedelta}.
                If None, uses DEFAULT_RATE_LIMITS.
    """

    def __init__(self, limits: Optional[dict[str, dict]] = None):
        self._limits = limits or DEFAULT_RATE_LIMITS
        self._counters: dict[str, _Counter] = defaultdict(
            lambda: _Counter(reset_time=datetime.now())
        )

    def _roll(self, action_type: str, config: dict) -> _Counter:
        """Return the bucket's counter, resetting it if its window elapsed."""
        counter = self._counters[action_type]
        now = datetime.now()
        if now >= counter.reset_time:
            counter.count = 0
            counter.reset_time = now + config["window"]
        return counter

    def check(self, action_type: str) -> bool:
        """Return True if the action is within rate limits, False otherwise.

        Rolls the window forward if it has elapsed, but never increments the
        count — call :meth:`consume` to count and check in one step.
        """
        config = self._limits.get(action_type)
        if config is None:
            return True
        counter = self._roll(action_type, config)
        return counter.count < config["limit"]

    def consume(self, action_type: str) -> None:
        """Increment the counter for *action_type* and raise if over limit.

        Raises:
            RateLimitExceeded: If the bucket is exhausted.
        """
        config = self._limits.get(action_type)
        if config is None:
            return
        counter = self._roll(action_type, config)
        if counter.count >= config["limit"]:
            raise RateLimitExceeded(action_type, reset_at=counter.reset_time)
        counter.count += 1

    def reset(self, action_type: Optional[str] = None) -> None:
        """Reset counters. If *action_type* is None, reset all buckets."""
        if action_type:
            self._counters.pop(action_type, None)
        else:
            self._counters.clear()
