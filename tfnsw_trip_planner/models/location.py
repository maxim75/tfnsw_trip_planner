"""Location model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coordinate import Coordinate
from .enums import LocationType
from .stop_parent import StopParent


@dataclass
class Location:
    """A location returned by the Stop Finder or Coordinate API."""
    id: str
    name: str
    type: LocationType
    coord: Coordinate | None
    modes: list[int]
    match_quality: int
    is_best: bool
    parent: StopParent | None
    building_number: str
    street_name: str
    properties: dict[str, Any]
    distance: int | None

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        coord_raw = data.get("coord")
        parent_raw = data.get("parent")
        props = data.get("properties", {})

        # The coord API returns sparse top-level fields; fall back to properties.
        raw_id = str(
            data.get("id")
            or props.get("STOP_GLOBAL_ID")
            or props.get("stopId")
            or ""
        )
        raw_name = props.get("STOP_NAME_WITH_PLACE") or ""

        # modes: top-level list wins; fall back to STOP_MOT_LIST (e.g. "1,4,5,9")
        raw_modes: list[int] = data.get("modes") or []
        if not raw_modes:
            mot_str = props.get("STOP_MOT_LIST", "")
            if mot_str:
                try:
                    raw_modes = [int(x) for x in str(mot_str).split(",") if x.strip()]
                except ValueError:
                    raw_modes = []

        distance_raw = props.get("distance")
        try:
            distance = int(distance_raw) if distance_raw is not None else None
        except (TypeError, ValueError):
            distance = None

        return cls(
            id=raw_id,
            name=raw_name,
            type=LocationType(data.get("type", "unknown"))
                if data.get("type") in LocationType._value2member_map_ else LocationType.UNKNOWN,
            coord=Coordinate.from_list(coord_raw) if coord_raw else None,
            modes=raw_modes,
            match_quality=data.get("matchQuality", 0),
            is_best=data.get("isBest", False),
            parent=StopParent.from_dict(parent_raw) if parent_raw else None,
            building_number=data.get("buildingNumber", ""),
            street_name=data.get("streetName", ""),
            properties=props,
            distance=distance,
        )

    def __repr__(self) -> str:
        dist = f", distance={self.distance}m" if self.distance is not None else ""
        return f"Location(id={self.id!r}, name={self.name!r}, type={self.type}{dist})"
