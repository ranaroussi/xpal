"""Exception hierarchy for xpal."""


class XPalError(Exception):
    """Base exception for all xpal errors."""


class AuthenticationError(XPalError):
    """Raised when credentials are missing or invalid."""


class RateLimitExceeded(XPalError):
    """Raised when an action exceeds its configured rate limit.

    Attributes:
        action_type: The rate-limit bucket that was exceeded.
        reset_at: When the limit window resets (datetime).
    """

    def __init__(self, action_type: str, reset_at=None):
        self.action_type = action_type
        self.reset_at = reset_at
        super().__init__(
            f"Rate limit exceeded for '{action_type}'"
            + (f", resets at {reset_at}" if reset_at else "")
        )
