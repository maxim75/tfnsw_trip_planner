"""Coordinate model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Coordinate:
    latitude: float
    longitude: float

    @classmethod
    def from_list(cls, coords: list[float]) -> "Coordinate | None":
        if coords and len(coords) >= 2:
            return cls(latitude=coords[0], longitude=coords[1])
        return None

    def to_api_string(self) -> str:
        """Return coordinate in TfNSW API format (longitude:latitude:EPSG:4326)."""
        return f"{self.longitude:.6f}:{self.latitude:.6f}:EPSG:4326"

    def __repr__(self) -> str:
        return f"Coordinate(lat={self.latitude}, lon={self.longitude})"
