"""Transport-related enumerations."""
from __future__ import annotations

from enum import Enum


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


class CyclingProfile(str, Enum):
    EASIER = "EASIER"
    MODERATE = "MODERATE"
    MORE_DIRECT = "MORE_DIRECT"
