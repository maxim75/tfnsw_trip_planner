"""VehiclePosition model (GTFS-Realtime Vehicle Positions feed)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .coordinate import Coordinate

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


@dataclass
class VehiclePosition:
    """A single vehicle's real-time position from the GTFS-Realtime feed.

    Unlike the Trip Planner endpoints (which return real-time *timing*), this
    is the live GPS location reported by the vehicle itself.
    """
    vehicle_id: str | None
    trip_id: str | None
    route_id: str | None
    latitude: float
    longitude: float
    bearing: float | None
    speed: float | None
    timestamp: datetime | None

    @classmethod
    def from_entity(cls, entity: Any) -> "VehiclePosition | None":
        """Build from a GTFS-Realtime ``FeedEntity`` protobuf message.

        Returns ``None`` for entities that carry no vehicle position.
        """
        if not entity.HasField("vehicle"):
            return None
        vp = entity.vehicle
        pos = vp.position
        ts = (
            datetime.fromtimestamp(vp.timestamp, tz=timezone.utc).astimezone(_SYDNEY_TZ)
            if vp.timestamp
            else None
        )
        return cls(
            vehicle_id=vp.vehicle.id or None,
            trip_id=vp.trip.trip_id or None,
            route_id=vp.trip.route_id or None,
            latitude=pos.latitude,
            longitude=pos.longitude,
            bearing=pos.bearing if pos.HasField("bearing") else None,
            speed=pos.speed if pos.HasField("speed") else None,
            timestamp=ts,
        )

    @property
    def coord(self) -> Coordinate:
        return Coordinate(latitude=self.latitude, longitude=self.longitude)

    def __repr__(self) -> str:
        return (
            f"VehiclePosition(vehicle={self.vehicle_id!r}, "
            f"route={self.route_id!r}, "
            f"lat={self.latitude}, lon={self.longitude})"
        )
