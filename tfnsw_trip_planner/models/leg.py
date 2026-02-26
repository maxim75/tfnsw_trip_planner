"""Leg model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coordinate import Coordinate
from .enums import TransportMode
from .hint import Hint
from .service_alert import ServiceAlert
from .stop import Stop
from .transport import Transport
from .travel_in_cars import TravelInCars


@dataclass
class Leg:
    """A single leg of a journey."""
    duration: int  # seconds
    origin: Stop
    destination: Stop
    transportation: Transport
    stop_sequence: list[Stop]
    coords: list[Coordinate]
    infos: list[ServiceAlert]
    hints: list[Hint]
    properties: dict[str, Any]
    is_realtime: bool

    @classmethod
    def from_dict(cls, data: dict) -> "Leg":
        origin = Stop.from_dict(data.get("origin", {}))
        destination = Stop.from_dict(data.get("destination", {}))
        transport = Transport.from_dict(data.get("transportation", {}))

        stop_seq = [Stop.from_dict(s) for s in data.get("stopSequence", [])]
        raw_coords = data.get("coords", [])
        coords = [c for item in raw_coords if (c := Coordinate.from_list(item))]

        infos = [ServiceAlert.from_dict(a) for a in data.get("infos", [])]
        hints = [Hint.from_dict(h) for h in data.get("hints", [])]

        props = data.get("properties", {})
        is_rt = bool(origin.departure_estimated or destination.arrival_estimated)

        return cls(
            duration=data.get("duration", 0),
            origin=origin,
            destination=destination,
            transportation=transport,
            stop_sequence=stop_seq,
            coords=coords,
            infos=infos,
            hints=hints,
            properties=props,
            is_realtime=is_rt,
        )

    @property
    def mode(self) -> TransportMode:
        return self.transportation.mode

    @property
    def low_floor_vehicle(self) -> bool:
        return self.properties.get("PlanLowFloorVehicle") == "1"

    @property
    def wheelchair_accessible_vehicle(self) -> bool:
        return self.properties.get("PlanWheelChairAccess") == "1"

    @property
    def travel_in_cars(self) -> TravelInCars | None:
        return TravelInCars.from_properties(self.origin.properties)

    def __repr__(self) -> str:
        return (
            f"Leg(mode={self.mode}, "
            f"from={self.origin.disassembled_name!r}, "
            f"to={self.destination.disassembled_name!r}, "
            f"duration={self.duration // 60}min)"
        )
