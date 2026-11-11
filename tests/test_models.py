"""Model parsing from rapidJSON-shaped dicts."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tfnsw_trip_planner import Journey, Leg, ServiceAlert, StopEvent, TransportMode
from tfnsw_trip_planner.models import TravelInCars

SYDNEY = ZoneInfo("Australia/Sydney")


def leg(dep: str, arr: str, duration: int, product_class: int = 1, **origin_extra: object) -> dict:
    return {
        "duration": duration,
        "origin": {"departureTimePlanned": dep, "disassembledName": "A", **origin_extra},
        "destination": {"arrivalTimePlanned": arr, "disassembledName": "B"},
        "transportation": {"product": {"class": product_class, "name": "x", "iconId": 1}},
    }


class TestTransportMode:
    def test_metro_is_recognised(self):
        # Sydney Metro is product class 2 ("Sydney Metro Network").
        assert TransportMode.from_class(2) is TransportMode.METRO

    def test_unknown_class(self):
        assert TransportMode.from_class(12345) is TransportMode.UNKNOWN

    def test_metro_leg_summary(self):
        j = Journey.from_dict(
            {"legs": [leg("2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z", 600, product_class=2)]}
        )
        assert j.legs[0].mode is TransportMode.METRO
        assert j.summary == "Metro"


class TestJourney:
    def test_total_duration_includes_transfer_wait(self):
        # 10 min train, 5 min wait, 20 min bus: door-to-door is 35 min, not 30.
        j = Journey.from_dict(
            {
                "legs": [
                    leg("2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z", 600, product_class=1),
                    leg("2026-01-01T00:15:00Z", "2026-01-01T00:35:00Z", 1200, product_class=5),
                ]
            }
        )
        assert j.total_duration == 35 * 60
        assert j.summary == "Train → Bus"
        assert "duration=35min" in repr(j)

    def test_total_duration_uses_realtime_estimates(self):
        data = leg("2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z", 600)
        data["destination"]["arrivalTimeEstimated"] = "2026-01-01T00:13:00Z"
        assert Journey.from_dict({"legs": [data]}).total_duration == 13 * 60

    def test_total_duration_falls_back_to_leg_sum(self):
        j = Journey.from_dict({"legs": [{"duration": 120}, {"duration": 60}]})
        assert j.departure_time is None
        assert j.total_duration == 180

    def test_empty(self):
        j = Journey.from_dict({})
        assert (j.departure_time, j.arrival_time, j.total_duration) == (None, None, 0)

    def test_times_are_sydney_local(self):
        j = Journey.from_dict({"legs": [leg("2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z", 600)]})
        assert j.departure_time == datetime(2026, 1, 1, 11, 0, tzinfo=SYDNEY)
        assert j.departure_time.tzinfo == SYDNEY


class TestLeg:
    def test_realtime_and_properties(self):
        data = leg("2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z", 600)
        data["origin"]["departureTimeEstimated"] = "2026-01-01T00:01:00Z"
        data["properties"] = {"PlanLowFloorVehicle": "1", "PlanWheelChairAccess": "0"}
        data["coords"] = [[-33.8, 151.2], [1.0], [-33.9, 151.3]]
        result = Leg.from_dict(data)
        assert result.is_realtime
        assert result.low_floor_vehicle
        assert not result.wheelchair_accessible_vehicle
        assert len(result.coords) == 2  # malformed coordinate dropped

    def test_travel_in_cars(self):
        data = leg(
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:10:00Z",
            600,
            properties={"NumberOfCars": "8", "TravelInCarsFrom": "1", "TravelInCarsTo": "4"},
        )
        tic = Leg.from_dict(data).travel_in_cars
        assert tic == TravelInCars(number_of_cars=8, from_car=1, to_car=4, message="")


class TestStopEvent:
    def test_estimated_wins_over_planned(self):
        ev = StopEvent.from_dict(
            {
                "departureTimePlanned": "2026-01-01T00:00:00Z",
                "departureTimeEstimated": "2026-01-01T00:02:00Z",
                "transportation": {"number": "T1", "destination": {"name": "Penrith"}},
            }
        )
        assert ev.is_realtime
        assert ev.departure_time == datetime(2026, 1, 1, 11, 2, tzinfo=SYDNEY)
        assert ev.transportation.destination_name == "Penrith"

    def test_minutes_until_departure(self):
        soon = (datetime.now(tz=SYDNEY) + timedelta(minutes=10, seconds=30)).isoformat()
        ev = StopEvent.from_dict({"departureTimePlanned": soon})
        assert not ev.is_realtime
        assert ev.minutes_until_departure in (9, 10)

    def test_departed_clamps_to_zero(self):
        ev = StopEvent.from_dict({"departureTimePlanned": "2020-01-01T00:00:00Z"})
        assert ev.minutes_until_departure == 0

    def test_null_fields(self):
        ev = StopEvent.from_dict(
            {"location": None, "transportation": None, "onwardLocations": None}
        )
        assert ev.departure_time is None
        assert ev.minutes_until_departure is None
        assert ev.travel_in_cars() == []


class TestServiceAlert:
    def test_parses_timestamp_and_affected(self):
        alert = ServiceAlert.from_dict(
            {
                "subtitle": "Lift outage",
                "url": "https://example.invalid/a",
                "timestamps": {"lastModification": "2026-01-01T00:00:00Z"},
                "affected": {"stops": [{"id": "200060"}], "lines": None},
            }
        )
        assert alert.last_modification == datetime(2026, 1, 1, 11, 0, tzinfo=SYDNEY)
        assert alert.affected_stops == [{"id": "200060"}]
        assert alert.affected_lines == []

    def test_bad_timestamp(self):
        for value in ("not a date", 12345):
            alert = ServiceAlert.from_dict({"timestamps": {"lastModification": value}})
            assert alert.last_modification is None
