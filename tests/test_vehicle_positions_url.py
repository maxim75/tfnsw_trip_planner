"""Which API version each vehicle-position feed is requested from.

TfNSW superseded some feeds with a v2 endpoint; those 404 on v1. These tests
pin the URL the client builds, without touching the network.
"""
import pytest

from tfnsw_trip_planner.client import TripPlannerClient


class StubResponse:
    ok = True
    status_code = 200
    content = b""  # an empty FeedMessage parses fine and yields no entities


class StubSession:
    """Captures the URL instead of performing a request."""

    def __init__(self):
        self.headers = {}
        self.requested_url = None

    def get(self, url, params=None, timeout=None):
        self.requested_url = url
        return StubResponse()

    def close(self):
        pass


@pytest.fixture
def session():
    return StubSession()


@pytest.fixture
def client(session):
    return TripPlannerClient(api_key="test-key", session=session)


class TestVehiclePositionApiVersion:
    @pytest.mark.parametrize(
        "mode",
        ["buses", "nswtrains", "metro", "ferries/sydneyferries", "lightrail/newcastle"],
    )
    def test_v1_feeds_use_v1(self, client, session, mode):
        client.vehicle_positions(mode)

        assert session.requested_url == f"https://api.transport.nsw.gov.au/v1/gtfs/vehiclepos/{mode}"

    @pytest.mark.parametrize("mode", ["sydneytrains", "lightrail/innerwest"])
    def test_superseded_feeds_use_v2(self, client, session, mode):
        # Regression: these 404 on v1. Sydney Trains vehicle positions were
        # unreachable through this library entirely.
        client.vehicle_positions(mode)

        assert session.requested_url == f"https://api.transport.nsw.gov.au/v2/gtfs/vehiclepos/{mode}"

    def test_explicit_version_overrides_the_default(self, client, session):
        # metro answers on both; v1 is the default only for compatibility.
        client.vehicle_positions("metro", version="v2")

        assert session.requested_url == "https://api.transport.nsw.gov.au/v2/gtfs/vehiclepos/metro"

    def test_explicit_v1_can_be_forced_for_a_v2_feed(self, client, session):
        client.vehicle_positions("sydneytrains", version="v1")

        assert (
            session.requested_url
            == "https://api.transport.nsw.gov.au/v1/gtfs/vehiclepos/sydneytrains"
        )

    def test_leading_and_trailing_slashes_are_trimmed(self, client, session):
        client.vehicle_positions("/sydneytrains/")

        assert (
            session.requested_url
            == "https://api.transport.nsw.gov.au/v2/gtfs/vehiclepos/sydneytrains"
        )

    def test_unknown_feeds_default_to_v1(self, client, session):
        client.vehicle_positions("regionbuses/southerntablelands")

        assert session.requested_url.startswith("https://api.transport.nsw.gov.au/v1/")


class TestVehiclePositionModes:
    def test_every_v2_mode_is_also_advertised(self):
        # A feed that is requested from v2 but never listed would be invisible.
        assert TripPlannerClient.VEHICLE_POSITION_V2_MODES <= set(
            TripPlannerClient.VEHICLE_POSITION_MODES
        )

    def test_sydneytrains_is_advertised(self):
        assert "sydneytrains" in TripPlannerClient.VEHICLE_POSITION_MODES
