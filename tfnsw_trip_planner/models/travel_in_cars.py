"""TravelInCars model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TravelInCars:
    number_of_cars: int
    from_car: int
    to_car: int
    message: str

    @classmethod
    def from_properties(cls, props: dict) -> "TravelInCars | None":
        if "NumberOfCars" not in props and "numberOfCars" not in props:
            return None
        try:
            return cls(
                number_of_cars=int(props.get("NumberOfCars") or props.get("numberOfCars", 0)),
                from_car=int(props.get("TravelInCarsFrom") or props.get("travelInCarsFrom", 0)),
                to_car=int(props.get("TravelInCarsTo") or props.get("travelInCarsTo", 0)),
                message=props.get("TravelInCarsMessage") or props.get("travelInCarsMessage", ""),
            )
        except (TypeError, ValueError):
            return None

    def __repr__(self) -> str:
        return f"TravelInCars(cars={self.number_of_cars}, range={self.from_car}-{self.to_car}, msg={self.message!r})"
