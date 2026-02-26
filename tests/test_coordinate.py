"""Unit tests for the Coordinate model."""
import pytest
from tfnsw_trip_planner.models.coordinate import Coordinate


class TestCoordinateFromList:
    def test_valid_two_element_list(self):
        coord = Coordinate.from_list([51.5, -0.1])
        assert coord is not None
        assert coord.latitude == 51.5
        assert coord.longitude == -0.1

    def test_list_with_extra_elements_returns_none(self):
        assert Coordinate.from_list([-33.8688, 151.2093, 0.0]) is None

    def test_empty_list_returns_none(self):
        assert Coordinate.from_list([]) is None

    def test_single_element_list_returns_none(self):
        assert Coordinate.from_list([51.5]) is None

    def test_none_returns_none(self):
        assert Coordinate.from_list(None) is None


class TestCoordinateToApiString:
    def test_format(self):
        coord = Coordinate(latitude=-33.865143, longitude=151.209900)
        assert coord.to_api_string() == "151.209900:-33.865143:EPSG:4326"

    def test_precision_six_decimal_places(self):
        coord = Coordinate(latitude=-33.1, longitude=151.2)
        result = coord.to_api_string()
        # format is "lon:lat:EPSG:4326" — split on first two colons only
        parts = result.split(":")
        lon_part, lat_part = parts[0], parts[1]
        assert len(lon_part.split(".")[1]) == 6
        assert len(lat_part.split(".")[1]) == 6

    def test_order_is_longitude_then_latitude(self):
        coord = Coordinate(latitude=1.0, longitude=2.0)
        assert coord.to_api_string().startswith("2.000000:1.000000")


class TestCoordinateRepr:
    def test_repr(self):
        coord = Coordinate(latitude=-33.8688, longitude=151.2093)
        assert repr(coord) == "Coordinate(lat=-33.8688, lon=151.2093)"


class TestCoordinateEquality:
    def test_equal_coordinates(self):
        assert Coordinate(1.0, 2.0) == Coordinate(1.0, 2.0)

    def test_unequal_coordinates(self):
        assert Coordinate(1.0, 2.0) != Coordinate(1.0, 3.0)
