"""Journey model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .leg import Leg


@dataclass
class Journey:
    """A complete journey made up of one or more legs."""

    legs: list[Leg]

    @classmethod
    def from_dict(cls, data: dict) -> Journey:
        legs = [Leg.from_dict(leg) for leg in data.get("legs") or []]
        return cls(legs=legs)

    @property
    def departure_time(self) -> datetime | None:
        if self.legs:
            return self.legs[0].origin.departure_time
        return None

    @property
    def arrival_time(self) -> datetime | None:
        if self.legs:
            return self.legs[-1].destination.arrival_time
        return None

    @property
    def total_duration(self) -> int:
        """Total door-to-door duration in seconds, including transfer waits.

        Computed from ``arrival_time - departure_time`` (real-time where
        available). Summing leg durations would miss the time spent waiting
        between legs, so that is only the fallback when a time is missing.
        """
        departure, arrival = self.departure_time, self.arrival_time
        if departure is not None and arrival is not None:
            return int((arrival - departure).total_seconds())
        return sum(leg.duration for leg in self.legs)

    @property
    def summary(self) -> str:
        """Human-readable transport mode summary (e.g. 'Train → Ferry')."""
        modes = [leg.mode.name.replace("_", " ").title() for leg in self.legs]
        return " → ".join(modes)

    def __repr__(self) -> str:
        mins = self.total_duration // 60
        return f"Journey(legs={len(self.legs)}, duration={mins}min, summary={self.summary!r})"
