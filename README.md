# TfNSW Trip Planner — Python Client

A clean, idiomatic Python library for the [Transport for NSW Trip Planning APIs](https://opendata.transport.nsw.gov.au/node/601/exploreapi).

---

## Installation

```bash
pip install requests          # only external dependency
```

Copy the `tfnsw_trip_planner/` package into your project, then import it:

```python
from tfnsw_trip_planner import TripPlannerClient
```

---

## Quick Start

```python
from tfnsw_trip_planner import TripPlannerClient

client = TripPlannerClient(api_key="YOUR_API_KEY")
```

> Get your free API key at <https://opendata.transport.nsw.gov.au>

---

## Examples

### 1. Find a Stop

```python
locations = client.find_stop("Circular Quay")
for loc in locations:
    print(loc.name, loc.id, loc.coord)

# Get the best single match
best = client.best_stop("Domestic Airport")
print(best.id, best.name)
```

### 2. Plan a Trip

```python
from datetime import datetime

journeys = client.plan_trip(
    origin_id="10101331",       # Domestic Airport Station
    destination_id="10102027",  # Manly Wharf
)

for journey in journeys:
    print(journey)
    # Journey(legs=3, duration=61min, summary='Train → Walk → Bus')

    print(f"  Depart : {journey.departure_time}")
    print(f"  Arrive : {journey.arrival_time}")
    print(f"  Route  : {journey.summary}")

    fare = journey.fare_summary
    if fare:
        print(f"  Cost   : ${fare.price_total:.2f} ({fare.status.value})")
```

### 3. Arrive By a Specific Time

```python
from datetime import datetime

# Plan a trip that arrives by 6 PM today
arrive_by = datetime.now().replace(hour=18, minute=0)
journeys = client.plan_trip(
    origin_id="10101331",
    destination_id="10102027",
    when=arrive_by,
    arrive_by=True,
)
```

### 4. Directions from GPS Location

```python
journeys = client.plan_trip_from_coordinate(
    latitude=-33.884080,
    longitude=151.206290,
    destination_id="10102027",
)
```

### 5. Wheelchair-Accessible Trips Only

```python
journeys = client.plan_trip(
    origin_id="10101331",
    destination_id="10102027",
    wheelchair=True,
)

for journey in journeys:
    for leg in journey.legs:
        print(f"  {leg.transportation.number}")
        print(f"    Low-floor vehicle     : {leg.low_floor_vehicle}")
        print(f"    Wheelchair accessible : {leg.wheelchair_accessible_vehicle}")
        print(f"    Origin accessible     : {leg.origin.wheelchair_access}")
        print(f"    Destination accessible: {leg.destination.wheelchair_access}")
```

### 6. Cycling Trip

```python
from tfnsw_trip_planner import CyclingProfile

journeys = client.plan_cycling_trip(
    origin_id="10101331",
    destination_id="10102027",
    profile=CyclingProfile.MODERATE,
    bike_only=True,
)
```

### 7. Upcoming Departures (Departure Board)

```python
departures = client.get_departures("10101331")  # Domestic Airport

for event in departures:
    mins = event.minutes_until_departure
    rt   = "⚡" if event.is_realtime else "🕐"
    print(f"{rt} {mins:>3}m  {event.transportation.number:>8}  → {event.transportation.destination_name}")

# From a specific platform only
departures = client.get_departures("10101331", platform_id="202091")
```

### 8. Travel in Cars (Train Car Guidance)

```python
departures = client.get_departures("10101331")
for event in departures:
    for tic in event.travel_in_cars():
        print(
            f"Train has {tic.number_of_cars} cars. "
            f"Board cars {tic.from_car}–{tic.to_car} ({tic.message})"
        )
```

### 9. Service Alerts

```python
alerts = client.get_alerts()
for alert in alerts:
    print(alert.subtitle)
    print(f"  Affected stops: {len(alert.affected_stops)}")
    print(f"  Affected lines: {len(alert.affected_lines)}")

# Alerts for a specific stop
alerts = client.get_alerts(stop_id="10111010")  # Central Station
```

### 10. Nearby Stops / Opal Resellers

```python
# Stops within 500m
nearby = client.find_nearby(latitude=-33.884080, longitude=151.206290, radius_m=500)
for loc in nearby:
    print(loc.name, loc.properties.get("distance"), "m")

# Opal resellers within 1km
resellers = client.find_opal_resellers(latitude=-33.884080, longitude=151.206290)
for r in resellers:
    print(r.name, r.coord)
```

---

## Using as a Context Manager

```python
with TripPlannerClient(api_key="YOUR_KEY") as client:
    journeys = client.plan_trip("10101331", "10102027")
```

---

## API Reference

### `TripPlannerClient`

| Method | Description |
|---|---|
| `find_stop(query, ...)` | Search stops/POIs by name |
| `find_stop_by_id(stop_id)` | Look up a stop by its ID |
| `best_stop(query)` | Return the top-matching stop |
| `plan_trip(origin_id, destination_id, ...)` | Plan a journey |
| `plan_trip_from_coordinate(lat, lon, dest_id, ...)` | Trip from GPS coordinate |
| `plan_cycling_trip(origin_id, dest_id, ...)` | Cycling trip |
| `get_departures(stop_id, ...)` | Upcoming departures from a stop |
| `get_alerts(...)` | Service alerts |
| `find_nearby(lat, lon, ...)` | POIs near a coordinate |
| `find_opal_resellers(lat, lon, ...)` | Opal resellers near a coordinate |

### Key Models

| Model | Key Attributes |
|---|---|
| `Location` | `id`, `name`, `type`, `coord`, `modes`, `is_best` |
| `Journey` | `legs`, `departure_time`, `arrival_time`, `total_duration`, `summary`, `fare_summary` |
| `Leg` | `mode`, `origin`, `destination`, `duration`, `stop_sequence`, `coords`, `infos` |
| `Stop` | `id`, `name`, `departure_time`, `arrival_time`, `wheelchair_access` |
| `Transport` | `number`, `mode`, `destination_name` |
| `StopEvent` | `transportation`, `departure_time`, `is_realtime`, `minutes_until_departure` |
| `Fare` | `person`, `price_total`, `station_access_fee`, `status` |
| `ServiceAlert` | `subtitle`, `url`, `affected_stops`, `affected_lines` |
| `TravelInCars` | `number_of_cars`, `from_car`, `to_car`, `message` |

### `CyclingProfile` Enum

| Value | Description |
|---|---|
| `CyclingProfile.EASIER` | Avoids hills and busy roads |
| `CyclingProfile.MODERATE` | Intermediate — occasional hills |
| `CyclingProfile.MORE_DIRECT` | Fastest route, steeper hills allowed |

### `TransportMode` Enum

`TRAIN`, `LIGHT_RAIL`, `BUS`, `COACH`, `FERRY`, `SCHOOL_BUS`, `WALK`, `CYCLE`, `ON_DEMAND`

---

## Error Handling

```python
from tfnsw_trip_planner import APIError, NetworkError

try:
    journeys = client.plan_trip("10101331", "10102027")
except NetworkError as e:
    print("Network problem:", e)
except APIError as e:
    print(f"API error {e.status_code}:", e)
```
