"""StopEvent model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .stop import Stop
from .transport import Transport
from .travel_in_cars import TravelInCars

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
class StopEvent:
    """A single departure event from the Departure API."""
    location: Stop
    transportation: Transport
    departure_planned: datetime | None
    departure_estimated: datetime | None
    onwards_locations: list[dict]

    @classmethod
    def from_dict(cls, data: dict) -> "StopEvent":
        return cls(
            location=Stop.from_dict(data.get("location", {})),
            transportation=Transport.from_dict(data.get("transportation", {})),
            departure_planned=_parse_dt(data.get("departureTimePlanned")),
            departure_estimated=_parse_dt(data.get("departureTimeEstimated")),
            onwards_locations=data.get("onwardLocations", []),
        )

    @property
    def departure_time(self) -> datetime | None:
        return self.departure_estimated or self.departure_planned

    @property
    def is_realtime(self) -> bool:
        return self.departure_estimated is not None

    @property
    def minutes_until_departure(self) -> int | None:
        if self.departure_time:
            delta = self.departure_time - datetime.now(tz=self.departure_time.tzinfo)
            return max(0, int(delta.total_seconds() // 60))
        return None

    def travel_in_cars(self) -> list[TravelInCars]:
        result = []
        for loc in self.onwards_locations:
            tic = TravelInCars.from_properties(loc.get("properties", {}))
            if tic:
                result.append(tic)
        return result

    def __repr__(self) -> str:
        mins = self.minutes_until_departure
        mins_str = f"{mins}min" if mins is not None else "?"
        return (
            f"StopEvent(route={self.transportation.number!r}, "
            f"dest={self.transportation.destination_name!r}, "
            f"departure={mins_str})"
        )
