"""Custom exceptions for TfNSW Trip Planner client."""


class TripPlannerError(Exception):
    """Base exception for all Trip Planner errors."""


class APIError(TripPlannerError):
    """Raised when the API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NetworkError(TripPlannerError):
    """Raised when a network/connectivity error occurs."""
