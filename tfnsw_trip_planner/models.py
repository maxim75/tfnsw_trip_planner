"""Data models for TfNSW Trip Planner API responses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransportMode(Enum):
    TRAIN = 1
    LIGHT_RAIL = 4
    BUS = 5
    COACH = 7
    FERRY = 9
    SCHOOL_BUS = 11
    WALK = 99
    WALK_ALT = 100
    CYCLE = 107
    ON_DEMAND = 23  # iconId-based identification
    UNKNOWN = -1

    @classmethod
    def from_class(cls, product_class: int) -> "TransportMode":
        try:
            return cls(product_class)
        except ValueError:
            return cls.UNKNOWN


class LocationType(str, Enum):
    STOP = "stop"
    PLATFORM = "platform"
    POI = "poi"
    ADDRESS = "singlehouse"
    LOCALITY = "locality"
    STREET = "street"
    UNKNOWN = "unknown"


class FareStatus(str, Enum):
    ENABLED = "nswFareEnabled"
    PARTIALLY_ENABLED = "nswFarePartiallyEnabled"
    NOT_ENABLED = "nswFareNotEnabled"
    NOT_AVAILABLE = "nswFareNotAvailable"


class CyclingProfile(str, Enum):
    EASIER = "EASIER"
    MODERATE = "MODERATE"
    MORE_DIRECT = "MORE_DIRECT"


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------

@dataclass
class Coordinate:
    latitude: float
    longitude: float

    @classmethod
    def from_list(cls, coords: list[float]) -> "Coordinate | None":
        if coords and len(coords) >= 2:
            return cls(latitude=coords[0], longitude=coords[1])
        return None

    def to_api_string(self) -> str:
        """Return coordinate in TfNSW API format (longitude:latitude:EPSG:4326)."""
        return f"{self.longitude:.6f}:{self.latitude:.6f}:EPSG:4326"

    def __repr__(self) -> str:
        return f"Coordinate(lat={self.latitude}, lon={self.longitude})"


# ---------------------------------------------------------------------------
# Stop / Location models
# ---------------------------------------------------------------------------

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


@dataclass
class Location:
    """A location returned by the Stop Finder or Coordinate API."""
    id: str
    name: str
    type: LocationType
    coord: Coordinate | None
    modes: list[int]
    match_quality: int
    is_best: bool
    parent: StopParent | None
    building_number: str
    street_name: str
    properties: dict[str, Any]
    disassembled_name: str

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        coord_raw = data.get("coord")
        parent_raw = data.get("parent")
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            type=LocationType(data.get("type", "unknown"))
                if data.get("type") in LocationType._value2member_map_ else LocationType.UNKNOWN,
            coord=Coordinate.from_list(coord_raw) if coord_raw else None,
            modes=data.get("modes", []),
            match_quality=data.get("matchQuality", 0),
            is_best=data.get("isBest", False),
            parent=StopParent.from_dict(parent_raw) if parent_raw else None,
            building_number=data.get("buildingNumber", ""),
            street_name=data.get("streetName", ""),
            properties=data.get("properties", {}),
            disassembled_name=data.get("disassembledName", ""),
        )

    def __repr__(self) -> str:
        return f"Location(id={self.id!r}, name={self.name!r}, type={self.type})"


# ---------------------------------------------------------------------------
# Transport / Product
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Stop / StopSequence
# ---------------------------------------------------------------------------

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
        def parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except (ValueError, TypeError):
                return None

        props = data.get("properties", {})
        wc = props.get("WheelchairAccess", "false")
        coord_raw = data.get("coord")
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            disassembled_name=data.get("disassembledName", ""),
            coord=Coordinate.from_list(coord_raw) if coord_raw else None,
            departure_planned=parse_dt(data.get("departureTimePlanned")),
            departure_estimated=parse_dt(data.get("departureTimeEstimated")),
            arrival_planned=parse_dt(data.get("arrivalTimePlanned")),
            arrival_estimated=parse_dt(data.get("arrivalTimeEstimated")),
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


# ---------------------------------------------------------------------------
# Fares
# ---------------------------------------------------------------------------

@dataclass
class Fare:
    person: str
    price_brutto: float
    price_total: float
    station_access_fee: float
    status: FareStatus
    rider_category_name: str
    from_leg: int
    to_leg: int
    is_summary: bool

    @classmethod
    def from_dict(cls, data: dict) -> "Fare":
        props = data.get("properties", {})
        status_str = props.get("evaluationTicket", "")
        try:
            status = FareStatus(status_str)
        except ValueError:
            status = FareStatus.NOT_AVAILABLE

        return cls(
            person=data.get("person", ""),
            price_brutto=float(data.get("priceBrutto", 0) or 0),
            price_total=float(props.get("priceTotalFare", 0) or 0),
            station_access_fee=float(props.get("priceStationAccessFee", 0) or 0),
            status=status,
            rider_category_name=props.get("riderCategoryName", ""),
            from_leg=data.get("fromLeg", 0),
            to_leg=data.get("toLeg", 0),
            is_summary="evaluationTicket" in props,
        )

    def __repr__(self) -> str:
        return f"Fare(person={self.person!r}, total={self.price_total}, status={self.status})"


# ---------------------------------------------------------------------------
# Service Alerts / Hints
# ---------------------------------------------------------------------------

@dataclass
class ServiceAlert:
    subtitle: str
    url: str
    last_modification: datetime | None
    affected_stops: list[dict]
    affected_lines: list[dict]

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceAlert":
        timestamps = data.get("timestamps", {})
        modified_str = timestamps.get("lastModification")
        try:
            modified = datetime.fromisoformat(modified_str) if modified_str else None
        except ValueError:
            modified = None

        affected = data.get("affected", {})
        return cls(
            subtitle=data.get("subtitle", ""),
            url=data.get("url", ""),
            last_modification=modified,
            affected_stops=affected.get("stops", []),
            affected_lines=affected.get("lines", []),
        )

    def __repr__(self) -> str:
        return f"ServiceAlert(subtitle={self.subtitle!r})"


@dataclass
class Hint:
    text: str
    raw: dict

    @classmethod
    def from_dict(cls, data: dict) -> "Hint":
        return cls(text=data.get("infoText", ""), raw=data)


# ---------------------------------------------------------------------------
# Travel-in-Cars
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Leg
# ---------------------------------------------------------------------------

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
        is_rt = bool(
            origin.departure_estimated or destination.arrival_estimated
        )

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


# ---------------------------------------------------------------------------
# Journey
# ---------------------------------------------------------------------------

@dataclass
class Journey:
    """A complete journey made up of one or more legs."""
    legs: list[Leg]
    fares: list[Fare]

    @classmethod
    def from_dict(cls, data: dict) -> "Journey":
        legs = [Leg.from_dict(l) for l in data.get("legs", [])]
        fare_raw = data.get("fare", {})
        tickets = fare_raw.get("tickets", []) if fare_raw else []
        fares = [Fare.from_dict(t) for t in tickets]
        return cls(legs=legs, fares=fares)

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
        """Total duration in seconds."""
        return sum(leg.duration for leg in self.legs)

    @property
    def summary(self) -> str:
        """Human-readable transport mode summary (e.g. 'Train → Ferry')."""
        modes = [leg.mode.name.replace("_", " ").title() for leg in self.legs]
        return " → ".join(modes)

    @property
    def fare_summary(self) -> Fare | None:
        """Returns the total summary fare (ADULT by default if available)."""
        for fare in self.fares:
            if fare.is_summary and fare.person == "ADULT":
                return fare
        for fare in self.fares:
            if fare.is_summary:
                return fare
        return None

    def __repr__(self) -> str:
        mins = self.total_duration // 60
        return f"Journey(legs={len(self.legs)}, duration={mins}min, summary={self.summary!r})"


# ---------------------------------------------------------------------------
# StopEvent (Departures)
# ---------------------------------------------------------------------------

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
        def parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=_SYDNEY_TZ)
                return dt.astimezone(_SYDNEY_TZ)
            except (ValueError, TypeError):
                return None

        return cls(
            location=Stop.from_dict(data.get("location", {})),
            transportation=Transport.from_dict(data.get("transportation", {})),
            departure_planned=parse_dt(data.get("departureTimePlanned")),
            departure_estimated=parse_dt(data.get("departureTimeEstimated")),
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
