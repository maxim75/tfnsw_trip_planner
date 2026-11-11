"""TfNSW Trip Planner API - Python Client Library"""

from .client import TripPlannerClient
from .exceptions import APIError, NetworkError, RateLimitError, TripPlannerError
from .models import (
    Coordinate,
    CyclingProfile,
    Journey,
    Leg,
    Location,
    ServiceAlert,
    Stop,
    StopEvent,
    Transport,
    TransportMode,
    VehiclePosition,
)

__all__ = [
    "TripPlannerClient",
    "Location",
    "Journey",
    "Leg",
    "StopEvent",
    "ServiceAlert",
    "Stop",
    "Transport",
    "Coordinate",
    "CyclingProfile",
    "TransportMode",
    "VehiclePosition",
    "TripPlannerError",
    "APIError",
    "RateLimitError",
    "NetworkError",
]

__version__ = "1.5.0"
