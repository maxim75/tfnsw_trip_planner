"""ServiceAlert model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


@dataclass
class ServiceAlert:
    subtitle: str
    url: str
    last_modification: datetime | None
    affected_stops: list[dict]
    affected_lines: list[dict]

    @classmethod
    def from_dict(cls, data: dict) -> ServiceAlert:
        timestamps = data.get("timestamps") or {}
        modified_str = timestamps.get("lastModification")
        try:
            modified_dt = (
                datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
                if modified_str
                else None
            )
            modified = modified_dt.astimezone(_SYDNEY_TZ) if modified_dt else None
        except (AttributeError, TypeError, ValueError):
            modified = None

        affected = data.get("affected") or {}
        return cls(
            subtitle=data.get("subtitle", ""),
            url=data.get("url", ""),
            last_modification=modified,
            affected_stops=affected.get("stops") or [],
            affected_lines=affected.get("lines") or [],
        )

    def __repr__(self) -> str:
        return f"ServiceAlert(subtitle={self.subtitle!r})"
