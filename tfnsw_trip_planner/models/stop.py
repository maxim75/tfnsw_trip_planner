"""Stop model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .coordinate import Coordinate

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(_SYDNEY_TZ)
    except (ValueError, TypeError):
        return None


@dataclass
class Stop:
    """A stop within a leg's stop sequence."""
    id: str
    name: str
    disassembled_name: str
    coord: Coordinate | None
    departure_planned: datetime | None
    departure_estimated: datetime | None
    arrival_planned: datetime | None
    arrival_estimated: datetime | None
    wheelchair_access: bool
    properties: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict) -> "Stop":
        props = data.get("properties", {})
        wc = props.get("WheelchairAccess", "false")
        coord_raw = data.get("coord")
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            disassembled_name=data.get("disassembledName", ""),
            coord=Coordinate.from_list(coord_raw) if coord_raw else None,
            departure_planned=_parse_dt(data.get("departureTimePlanned")),
            departure_estimated=_parse_dt(data.get("departureTimeEstimated")),
            arrival_planned=_parse_dt(data.get("arrivalTimePlanned")),
            arrival_estimated=_parse_dt(data.get("arrivalTimeEstimated")),
            wheelchair_access=wc == "true",
            properties=props,
        )

    @property
    def departure_time(self) -> datetime | None:
        """Returns real-time estimate if available, else planned."""
        return self.departure_estimated or self.departure_planned

    @property
    def arrival_time(self) -> datetime | None:
        """Returns real-time estimate if available, else planned."""
        return self.arrival_estimated or self.arrival_planned

    def __repr__(self) -> str:
        return f"Stop(id={self.id!r}, name={self.disassembled_name!r})"
