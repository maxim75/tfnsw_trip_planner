"""Custom exceptions for TfNSW Trip Planner client."""

from __future__ import annotations


class TripPlannerError(Exception):
    """Base exception for all Trip Planner errors."""


class APIError(TripPlannerError):
    """Raised when the API returns an error response.

    ``status_code`` is the HTTP status. It is ``200`` when the HTTP request
    succeeded but the API reported an error in its ``systemMessages`` (for
    example an invalid stop ID); ``code`` then holds the API's error code.
    """

    def __init__(
        self, message: str, status_code: int | None = None, code: int | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class RateLimitError(APIError):
    """Raised when the API keeps answering 429 after the client's retries.

    ``retry_after`` is the server's requested wait in seconds, if it sent one.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class NetworkError(TripPlannerError):
    """Raised when a network/connectivity error occurs."""
