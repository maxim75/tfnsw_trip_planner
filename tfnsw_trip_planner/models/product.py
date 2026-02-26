"""Product model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Product:
    product_class: int
    name: str
    icon_id: int

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        return cls(
            product_class=data.get("class", -1),
            name=data.get("name", ""),
            icon_id=data.get("iconId", -1),
        )
