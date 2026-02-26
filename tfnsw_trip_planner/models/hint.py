"""Hint model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Hint:
    text: str
    raw: dict

    @classmethod
    def from_dict(cls, data: dict) -> "Hint":
        return cls(text=data.get("infoText", ""), raw=data)
