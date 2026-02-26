"""StopParent model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StopParent:
    id: str
    name: str
    type: str

    @classmethod
    def from_dict(cls, data: dict) -> "StopParent":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
        )
