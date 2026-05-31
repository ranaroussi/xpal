"""Exception hierarchy for xpal."""


class XPalError(Exception):
    """Base exception for all xpal errors."""


class AuthenticationError(XPalError):
    """Raised when credentials are missing or invalid."""


class XApiError(XPalError):
    """Raised when the X API returns an error response.

    Wraps the underlying Tweepy/HTTP error in a clean, single-line message.

    Attributes:
        status_code: HTTP status code returned by the API (if available).
        reset_at: When the server rate-limit window resets (datetime), parsed
            from the ``x-rate-limit-reset`` header on 429 responses.
    """

    def __init__(self, message: str, status_code=None, reset_at=None):
        self.status_code = status_code
        self.reset_at = reset_at
        super().__init__(
            message + (f" (rate limit resets at {reset_at})" if reset_at else "")
        )


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
