# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A clean, idiomatic Python client for the [Transport for NSW Trip Planning APIs](https://opendata.transport.nsw.gov.au/). Published to PyPI as `tfnsw-trip-planner`. The only hard runtime dependency is `requests`; `gtfs-realtime-bindings` is an optional `realtime` extra.

## Commands

```bash
# Run the test suite
python -m pytest tests/ -v

# Run a single test class / case
python -m pytest tests/test_coordinate.py::TestCoordinateToApiString -v
python -m pytest tests/test_coordinate.py -k "api_string" -v

# Install for development (with all extras)
pip install -e ".[dev,realtime]"

# Lint / format / type-check (configured in pyproject.toml)
black . && isort . && ruff check . && mypy tfnsw_trip_planner

# Build + publish (runs pytest first, then twine). test = TestPyPI, prod = PyPI
./build_and_publish.sh test

# Regenerate demo.md from the executed notebook (needs jupyter + nbconvert)
./build_demo.sh
```

Line length is 100 across black/isort/ruff. mypy targets Python 3.9; the library supports 3.9–3.13.

## Architecture

**Single client, many endpoints.** `TripPlannerClient` ([client.py](tfnsw_trip_planner/client.py)) is the only entry point. It wraps each TfNSW endpoint as one public method (`find_stop` → `stop_finder`, `plan_trip`/`plan_cycling_trip` → `trip`, `get_departures` → `departure_mon`, `get_alerts` → `add_info`, `find_nearby` → `coord`, `vehicle_positions` → GTFS-Realtime). Auth is a `Authorization: apikey <key>` header set in `__init__`.

**Two base URLs / two transports.** Trip-planning endpoints return rapidJSON and go through `_get()` (which merges `_COMMON_PARAMS`). The GTFS-Realtime vehicle-positions feed returns protobuf and goes through `_get_bytes()`; `vehicle_positions()` lazily imports `google.transit.gtfs_realtime_pb2` and raises a clear `ImportError` if the optional extra isn't installed. Keep the core install `requests`-only — do not add a top-level import of the GTFS bindings.

**Models: one dataclass per file, each owning its own parsing.** Everything in `tfnsw_trip_planner/models/` is a frozen-style dataclass with a `from_dict(data: dict)` classmethod (or `from_entity()` for the protobuf-backed `VehiclePosition`). Client methods are thin: fetch → map the relevant JSON array through `Model.from_dict`. When adding a field, edit the model's `from_dict`, not the client. New models must be exported from both `models/__init__.py` and the package `__init__.py`, and added to the README tables.

**Real-time = estimate-or-planned.** The TfNSW API returns both planned and estimated times. The convention throughout the models is: `departure_time`/`arrival_time` properties return `*_estimated or *_planned`, and `is_realtime` is derived from whether an estimate is present (see [stop.py](tfnsw_trip_planner/models/stop.py), [stop_event.py](tfnsw_trip_planner/models/stop_event.py), [leg.py](tfnsw_trip_planner/models/leg.py)). `vehicle_positions()` is different — it returns actual live GPS coordinates, not timing.

**All datetimes are Sydney-local.** Input times are normalised with `_to_sydney()` in the client; parsed API timestamps are converted to `Australia/Sydney` via a `_parse_dt()` helper that is intentionally duplicated in each model file that needs it. Keep that convention rather than centralising it inconsistently.

**Coordinate format gotcha.** The TfNSW API expects coordinates as `longitude:latitude:EPSG:4326` (lon first). `Coordinate.to_api_string()` and the inline `f"{longitude:.6f}:{latitude:.6f}:EPSG:4326"` strings encode this — don't swap the order.

**Errors.** Network failures raise `NetworkError`; non-2xx or unparseable responses raise `APIError` (with `status_code`). Both subclass `TripPlannerError`.

## Versioning

The version is duplicated in `pyproject.toml` (`project.version`) and `tfnsw_trip_planner/__init__.py` (`__version__`) — bump both together. Commit messages in this repo are conventionally prefixed with the new version (e.g. `v1.3.0: ...`).
