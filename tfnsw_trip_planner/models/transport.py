"""Transport model."""
from __future__ import annotations

from dataclasses import dataclass

from .enums import TransportMode
from .product import Product


@dataclass
class Transport:
    id: str
    name: str
    disassembled_name: str
    number: str
    icon_id: int
    description: str
    product: Product | None
    destination_name: str
    mode: TransportMode

    @classmethod
    def from_dict(cls, data: dict) -> "Transport":
        product_raw = data.get("product")
        product = Product.from_dict(product_raw) if product_raw else None
        mode = TransportMode.from_class(product.product_class) if product else TransportMode.UNKNOWN

        dest = data.get("destination", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            disassembled_name=data.get("disassembledName", ""),
            number=data.get("number", ""),
            icon_id=data.get("iconId", -1),
            description=data.get("description", ""),
            product=product,
            destination_name=dest.get("name", "") if dest else "",
            mode=mode,
        )

    def __repr__(self) -> str:
        return f"Transport(number={self.number!r}, mode={self.mode}, dest={self.destination_name!r})"
