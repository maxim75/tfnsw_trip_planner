"""Live integration tests for GTFS-Realtime vehicle positions.

These hit the *real* TfNSW API. They are skipped automatically unless:

  - the optional ``gtfs-realtime-bindings`` dependency is installed, and
  - the ``TFNSW_API_KEY`` environment variable is set (it is also read from a
    ``.env`` file at the repo root — see ``tests/conftest.py`` and ``.env.example``).

The API key must have the **Public Transport – Realtime Vehicle Positions**
product enabled (see the README "Getting an API Key" section); a key without it
returns 401/403 and the affected test is skipped with a hint.

Run them with::

    pip install -e ".[realtime]"
    TFNSW_API_KEY=your_key python -m pytest tests/test_vehicle_positions_live.py -v

Or select by marker::

    TFNSW_API_KEY=your_key python -m pytest -m integration -v
"""
import os
from datetime import datetime

import pytest

from tfnsw_trip_planner import APIError, TripPlannerClient, VehiclePosition

# Skip the whole module if the optional protobuf bindings aren't installed.
pytest.importorskip(
    "google.transit.gtfs_realtime_pb2",
    reason="vehicle positions require: pip install tfnsw-trip-planner[realtime]",
)

API_KEY = os.environ.get("TFNSW_API_KEY")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not API_KEY, reason="set TFNSW_API_KEY to run live API tests"),
]

# A spread of feeds across transport modes / endpoint shapes.
MODES = ["buses", "nswtrains", "metro", "ferries/sydneyferries"]


@pytest.fixture(scope="module")
def client():
    c = TripPlannerClient(api_key=API_KEY)
    yield c
    c.close()


# Cache one fetch per feed for the whole module so we don't re-hit the (rate
# limited) API for every test that needs the same mode.
_CACHE: dict[str, list[VehiclePosition]] = {}


def _fetch(client, mode):
    """Fetch a feed once, caching it; skip on auth or rate-limit responses."""
    if mode in _CACHE:
        return _CACHE[mode]
    try:
        positions = client.vehicle_positions(mode)
    except APIError as exc:
        if exc.status_code in (401, 403):
            pytest.skip(
                f"API key not authorised for vehiclepos/{mode} — add the "
                f"'Realtime Vehicle Positions' product to your application ({exc})"
            )
        if exc.status_code == 429:
            pytest.skip(f"rate limit / quota exceeded for vehiclepos/{mode} ({exc})")
        raise
    _CACHE[mode] = positions
    return positions


@pytest.mark.parametrize("mode", MODES)
def test_returns_list_of_vehicle_positions(client, mode):
    positions = _fetch(client, mode)
    assert isinstance(positions, list)
    # Empty is tolerated (e.g. a quiet feed outside service hours); when present,
    # every element must be a fully-formed VehiclePosition.
    assert all(isinstance(p, VehiclePosition) for p in positions)


def test_coordinates_within_nsw(client):
    positions = _fetch(client, "buses")
    if not positions:
        pytest.skip("no vehicles currently reporting on the buses feed")

    # Some vehicles report (0, 0) when they have no current GPS fix — that's a
    # genuine feed condition, not a parsing bug, so exclude them.
    located = [p for p in positions if not (p.latitude == 0.0 and p.longitude == 0.0)]
    if not located:
        pytest.skip("no vehicles with a GPS fix on the buses feed right now")

    for p in located:
        # Rough NSW bounding box — catches swapped lat/lon.
        assert -38.0 < p.latitude < -28.0, f"latitude out of range: {p.latitude}"
        assert 140.0 < p.longitude < 154.0, f"longitude out of range: {p.longitude}"
        # coord property mirrors the scalar fields.
        assert p.coord.latitude == p.latitude
        assert p.coord.longitude == p.longitude


def test_optional_fields_well_typed(client):
    positions = _fetch(client, "buses")
    if not positions:
        pytest.skip("no vehicles currently reporting on the buses feed")

    p = next(
        (vp for vp in positions if vp.bearing is not None or vp.timestamp is not None),
        positions[0],
    )
    if p.bearing is not None:
        assert 0.0 <= p.bearing <= 360.0
    if p.speed is not None:
        assert p.speed >= 0.0
    if p.timestamp is not None:
        assert isinstance(p.timestamp, datetime)
        # Timestamps are localised to Sydney by the model.
        assert p.timestamp.tzinfo is not None
    # Identifiers are either a non-empty string or None (never "").
    for field in (p.vehicle_id, p.route_id, p.trip_id):
        assert field is None or (isinstance(field, str) and field)
