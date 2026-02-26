# tfnsw-trip-planner — Demo Notebook

A hands-on walkthrough of every major feature in the [`tfnsw-trip-planner`](https://github.com/maxim75/tfnsw_trip_planner) library.

**Requirements**
- A Transport for NSW Open Data API key stored in a `.env` file as `TRANSPORT_NSW_API_KEY=<your_key>`.
- Python 3.9+

**Exporting to Markdown**

Run the following command from the project root to execute this notebook and produce `demo.md` with code *and* output embedded:

```bash
jupyter nbconvert --to markdown --execute demo.ipynb --output demo.md
```

> `jupyter` / `nbconvert` are **not** library dependencies — install them separately with `pip install jupyter nbconvert` or in a virtual environment of your choice.

## 1 · Setup & Imports


```python
%pip install --quiet tfnsw-trip-planner python-dotenv
```

    Note: you may need to restart the kernel to use updated packages.



```python
import datetime
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from tfnsw_trip_planner import CyclingProfile, TransportMode, TripPlannerClient

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")

tomorrow_9am = datetime.datetime.now(tz=_SYDNEY_TZ).replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
```

## 2 · Initialize the Client

The API key is read from a `.env` file in the project root:

```
TRANSPORT_NSW_API_KEY=your_key_here
```


```python
load_dotenv()

api_key = os.getenv("TRANSPORT_NSW_API_KEY")
assert api_key, "Set TRANSPORT_NSW_API_KEY in your .env file"

client = TripPlannerClient(api_key=api_key)
print(client)
```

    TripPlannerClient(base_url='https://api.transport.nsw.gov.au/v1/tp/')


## 3 · Find a Stop by Name

`find_stop()` queries the TfNSW Stop Finder and returns up to `max_results` locations sorted by match quality.  
Pass `location_type="stop"` to restrict results to transit stops only.


```python
locations = client.find_stop("Circular Quay", location_type="stop", max_results=5)

print(f"Found {len(locations)} stop(s):\n")
for loc in locations:
    modes = ", ".join(TransportMode.from_class(m).name.title() for m in loc.modes) if loc.modes else "—"
    print(f"  {loc.name}")
    print(f"    ID    : {loc.id}")
    print(f"    Coord : {loc.coord}")
    print(f"    Type  : {loc.type.value}")
    print(f"    Modes : {modes}")
    print()
```

    Found 1 stop(s):
    
      
        ID    : 200020
        Coord : Coordinate(lat=-33.861351, lon=151.210813)
        Type  : stop
        Modes : Train, Light_Rail, Bus, Ferry
    


## 4 · Get the Best Stop Match

`best_stop()` returns the single highest-confidence result — ideal when you just need one stop ID for downstream calls.


```python
for query in ["Central Station", "Domestic Airport", "Manly Wharf", "Bondi Junction"]:
    stop = client.best_stop(query)
    if stop:
        print(f"{query:<25}  →  ID: {stop.id:<15}  {stop.name}")
    else:
        print(f"{query:<25}  →  (no result)")
```

    Central Station            →  ID: 200060           
    Domestic Airport           →  ID: 202020           


    Manly Wharf                →  ID: 209573           


    Bondi Junction             →  ID: 202210           


## 5 · Get Departures from a Stop

`get_departures()` returns upcoming `StopEvent` objects for a given stop.  
⚡ = real-time data  🕐 = scheduled only


```python
# Domestic Airport Station (stop 2233133), 09:00 on a weekday
departures = client.get_departures("200020", when=tomorrow_9am)

print(f"Next {min(10, len(departures))} departures from Domestic Airport at {tomorrow_9am:%H:%M %d/%m/%Y}:\n")
for event in departures[:10]:
    rt    = "⚡" if event.is_realtime else "🕐"
    mins  = event.minutes_until_departure
    svc   = event.transportation.number or "—"
    dest  = event.transportation.destination_name or "—"
    dep_t = event.departure_time
    print(f"  {rt}  {mins:>4}m   {dep_t:%H:%M}   {svc:>8}   → {dest}")
```

    Next 10 departures from Domestic Airport at 09:00 27/02/2026:
    
      🕐   606m   09:00   T8 Airport & South Line   → Sydenham
      🕐   606m   09:00   CCWB Watsons Bay Ferry   → Watsons Bay
      🕐   606m   09:00   F6 Mosman Bay   → Mosman Bay
      🕐   606m   09:00        343   → Kingsford
      🕐   606m   09:00        396   → Maroubra Beach
      🕐   608m   09:02        333   → North Bondi
      🕐   608m   09:02   L2 Randwick Line   → Randwick
      🕐   609m   09:03   T8 Airport & South Line   → Macarthur via Airport
      🕐   610m   09:04   T2 Leppington & Inner West Line   → Leppington via Granville
      🕐   611m   09:05   CCSH Shark Island Ferry   → Shark Island


## 6 · Plan a Trip Between Two Stops

`plan_trip()` returns a list of `Journey` objects, each containing ordered `Leg` objects.

### 6a — Depart-by trip (default)

Domestic Airport → Manly Wharf, departing at 09:00.


```python
def print_journeys(journeys):
    for i, journey in enumerate(journeys, 1):
        print(f"Journey {i}: {journey}")
        print(f"  Depart : {journey.departure_time:%H:%M %d/%m/%Y %Z}")
        print(f"  Arrive : {journey.arrival_time:%H:%M %d/%m/%Y %Z}")
        print(f"  Route  : {journey.summary}")
        print()
        for leg in journey.legs:
            route    = leg.transportation.number or leg.mode.name.title()
            dest     = leg.transportation.destination_name or "—"
            dep_t    = leg.origin.departure_time
            arr_t    = leg.destination.arrival_time
            plat     = leg.origin.properties.get("platform") or ""
            plat_str = f"  Platform {plat}" if plat else ""
            rt       = "⚡" if leg.is_realtime else "  "
            print(f"    {rt} {leg.mode.name:<12} {route:<10}  → {dest}")
            print(f"         From : {leg.origin.name}{plat_str}")
            print(f"         Dep  : {dep_t:%H:%M}" if dep_t else "         Dep  : —")
            print(f"         To   : {leg.destination.name}")
            print(f"         Arr  : {arr_t:%H:%M}" if arr_t else "         Arr  : —")
        print("-" * 60)


journeys = client.plan_trip(
    origin_id="223310",   # Engadine Station
    destination_id="200070", # Town Hall Station
    when=tomorrow_9am,
)
print(f"Depart-by trip · Domestic Airport → Manly Wharf · Dep {tomorrow_9am:%H:%M}\n")
print_journeys(journeys)
```

    Depart-by trip · Domestic Airport → Manly Wharf · Dep 09:00
    
    Journey 1: Journey(legs=1, duration=43min, summary='Train')
      Depart : 09:01 27/02/2026 AEDT
      Arrive : 09:44 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        T4 Eastern Suburbs & Illawarra Line  → Bondi Junction via Wolli Creek
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 09:01
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 09:44
    ------------------------------------------------------------
    Journey 2: Journey(legs=1, duration=49min, summary='Train')
      Depart : 09:32 27/02/2026 AEDT
      Arrive : 10:21 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        T4 Eastern Suburbs & Illawarra Line  → Bondi Junction via Banksia
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 09:32
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 10:21
    ------------------------------------------------------------
    Journey 3: Journey(legs=1, duration=49min, summary='Train')
      Depart : 10:02 27/02/2026 AEDT
      Arrive : 10:51 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        T4 Eastern Suburbs & Illawarra Line  → Bondi Junction via Banksia
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 10:02
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 10:51
    ------------------------------------------------------------
    Journey 4: Journey(legs=1, duration=49min, summary='Train')
      Depart : 10:32 27/02/2026 AEDT
      Arrive : 11:21 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        T4 Eastern Suburbs & Illawarra Line  → Bondi Junction via Banksia
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 10:32
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 11:21
    ------------------------------------------------------------


### 6b — Arrive-by trip

Set `arrive_by=True` to find journeys that arrive at the destination *by* a specified time.


```python
journeys = client.plan_trip(
    origin_id="223310",   # Engadine Station
    destination_id="200070",  # Town Hall Station
    arrive_by=True,
    when=tomorrow_9am,
)
print(f"Arrive-by trip · Engadine Station → Town Hall · Arr by {tomorrow_9am:%H:%M}\n")
print_journeys(journeys)
```

    Arrive-by trip · Engadine Station → Town Hall · Arr by 09:00
    
    Journey 1: Journey(legs=1, duration=43min, summary='Train')
      Depart : 08:01 27/02/2026 AEDT
      Arrive : 08:44 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        South Coast Line  → Bondi Junction via Wolli Creek
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 08:01
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 08:44
    ------------------------------------------------------------
    Journey 2: Journey(legs=1, duration=43min, summary='Train')
      Depart : 07:41 27/02/2026 AEDT
      Arrive : 08:24 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        T4 Eastern Suburbs & Illawarra Line  → Bondi Junction via Wolli Creek
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 07:41
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 08:24
    ------------------------------------------------------------
    Journey 3: Journey(legs=1, duration=43min, summary='Train')
      Depart : 07:21 27/02/2026 AEDT
      Arrive : 08:04 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        T4 Eastern Suburbs & Illawarra Line  → Bondi Junction via Wolli Creek
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 07:21
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 08:04
    ------------------------------------------------------------
    Journey 4: Journey(legs=1, duration=43min, summary='Train')
      Depart : 07:01 27/02/2026 AEDT
      Arrive : 07:44 27/02/2026 AEDT
      Route  : Train
    
        ⚡ TRAIN        South Coast Line  → Bondi Junction via Wolli Creek
             From : Engadine Station, Platform 1, Engadine  Platform EGD1
             Dep  : 07:01
             To   : Town Hall Station, Platform 5, Sydney
             Arr  : 07:44
    ------------------------------------------------------------


## 7 · Plan a Trip from a GPS Coordinate

`plan_trip_from_coordinate()` lets you use a raw latitude/longitude as the origin — useful for mobile apps.


```python
# Approximate coordinates of the Sydney Opera House
lat, lon = -33.8568, 151.2153

when = datetime.datetime(2026, 2, 27, 9, 0, tzinfo=_SYDNEY_TZ)
journeys = client.plan_trip_from_coordinate(
    latitude=lat,
    longitude=lon,
    destination_id="10102027",  # Manly Wharf
    when=when,
)
print(f"From coordinate ({lat}, {lon}) → Manly Wharf · Dep {when:%H:%M}\n")
print_journeys(journeys)
```

    From coordinate (-33.8568, 151.2153) → Manly Wharf · Dep 09:00
    
    Journey 1: Journey(legs=2, duration=33min, summary='Walk Alt → Ferry')
      Depart : 09:12 27/02/2026 AEDT
      Arrive : 09:45 27/02/2026 AEDT
      Route  : Walk Alt → Ferry
    
        ⚡ WALK_ALT     Walk_Alt    → —
             From : 2 Circular Quay East, Sydney
             Dep  : 09:12
             To   : Circular Quay, Sydney
             Arr  : 09:25
        ⚡ FERRY        MFF Manly Fast Ferry  → Manly
             From : Circular Quay, Wharf 2, Side A, Sydney  Platform F2A
             Dep  : 09:25
             To   : Manly Wharf, Wharf 2, Manly
             Arr  : 09:45
    ------------------------------------------------------------
    Journey 2: Journey(legs=2, duration=35min, summary='Walk Alt → Ferry')
      Depart : 09:17 27/02/2026 AEDT
      Arrive : 09:52 27/02/2026 AEDT
      Route  : Walk Alt → Ferry
    
        ⚡ WALK_ALT     Walk_Alt    → —
             From : 2 Circular Quay East, Sydney
             Dep  : 09:17
             To   : Circular Quay, Sydney
             Arr  : 09:30
        ⚡ FERRY        F1 Manly    → Manly
             From : Circular Quay, Wharf 3, Side A, Sydney  Platform F3A
             Dep  : 09:30
             To   : Manly Wharf, Wharf 1, Manly
             Arr  : 09:52
    ------------------------------------------------------------
    Journey 3: Journey(legs=2, duration=33min, summary='Walk Alt → Ferry')
      Depart : 09:32 27/02/2026 AEDT
      Arrive : 10:05 27/02/2026 AEDT
      Route  : Walk Alt → Ferry
    
        ⚡ WALK_ALT     Walk_Alt    → —
             From : 2 Circular Quay East, Sydney
             Dep  : 09:32
             To   : Circular Quay, Sydney
             Arr  : 09:45
        ⚡ FERRY        MFF Manly Fast Ferry  → Manly
             From : Circular Quay, Wharf 2, Side A, Sydney  Platform F2A
             Dep  : 09:45
             To   : Manly Wharf, Wharf 2, Manly
             Arr  : 10:05
    ------------------------------------------------------------
    Journey 4: Journey(legs=2, duration=35min, summary='Walk Alt → Ferry')
      Depart : 09:32 27/02/2026 AEDT
      Arrive : 10:07 27/02/2026 AEDT
      Route  : Walk Alt → Ferry
    
        ⚡ WALK_ALT     Walk_Alt    → —
             From : 2 Circular Quay East, Sydney
             Dep  : 09:32
             To   : Circular Quay, Sydney
             Arr  : 09:45
        ⚡ FERRY        F1 Manly    → Manly
             From : Circular Quay, Wharf 3, Side A, Sydney  Platform F3A
             Dep  : 09:45
             To   : Manly Wharf, Wharf 1, Manly
             Arr  : 10:07
    ------------------------------------------------------------
    Journey 5: Journey(legs=2, duration=43min, summary='Walk Alt → Ferry')
      Depart : 09:37 27/02/2026 AEDT
      Arrive : 10:20 27/02/2026 AEDT
      Route  : Walk Alt → Ferry
    
        ⚡ WALK_ALT     Walk_Alt    → —
             From : 2 Circular Quay East, Sydney
             Dep  : 09:37
             To   : Circular Quay, Sydney
             Arr  : 09:50
        ⚡ FERRY        F1 Manly    → Manly
             From : Circular Quay, Wharf 3, Side B, Sydney  Platform F3B
             Dep  : 09:50
             To   : Manly Wharf, Wharf 1, Manly
             Arr  : 10:20
    ------------------------------------------------------------
    Journey 6: Journey(legs=2, duration=33min, summary='Walk Alt → Ferry')
      Depart : 09:47 27/02/2026 AEDT
      Arrive : 10:20 27/02/2026 AEDT
      Route  : Walk Alt → Ferry
    
        ⚡ WALK_ALT     Walk_Alt    → —
             From : 2 Circular Quay East, Sydney
             Dep  : 09:47
             To   : Circular Quay, Sydney
             Arr  : 10:00
        ⚡ FERRY        MFF Manly Fast Ferry  → Manly
             From : Circular Quay, Wharf 2, Side A, Sydney  Platform F2A
             Dep  : 10:00
             To   : Manly Wharf, Wharf 2, Manly
             Arr  : 10:20
    ------------------------------------------------------------


## 8 · Plan a Cycling Trip

`plan_cycling_trip()` returns bike-only (or bike + transit) routes.  
The `CyclingProfile` enum controls route preference: `EASIER`, `MODERATE`, or `MORE_DIRECT`.


```python
when = datetime.datetime(2026, 2, 27, 9, 0, tzinfo=_SYDNEY_TZ)
journeys = client.plan_cycling_trip(
    origin_id="10101331",      # Circular Quay Station
    destination_id="10102027", # Manly Wharf
    profile=CyclingProfile.MODERATE,
    when=when,
)

if journeys:
    print(f"Cycling trip · Circular Quay → Manly Wharf\n")
    print_journeys(journeys)
else:
    print("No cycling routes found (cycling may not be feasible for this O/D pair).")
```

    Cycling trip · Circular Quay → Manly Wharf
    
    Journey 1: Journey(legs=1, duration=129min, summary='Cycle')
      Depart : 09:00 27/02/2026 AEDT
      Arrive : 11:09 27/02/2026 AEDT
      Route  : Cycle
    
        ⚡ CYCLE        Cycle       → —
             From : Domestic Airport Station, Mascot
             Dep  : 09:00
             To   : Manly Wharf, Manly
             Arr  : 11:09
    ------------------------------------------------------------


## 9 · Service Alerts

`get_alerts()` retrieves current TfNSW service disruptions and planned works.  
Filter by stop with the `stop_id` parameter.


```python
alerts = client.get_alerts()

if alerts:
    print(f"{len(alerts)} current alert(s):\n")
    for alert in alerts[:5]:
        modified = alert.last_modification.strftime("%d/%m/%Y %H:%M") if alert.last_modification else "—"
        stops    = len(alert.affected_stops)
        lines    = len(alert.affected_lines)
        print(f"  {alert.subtitle}")
        print(f"    Last updated : {modified}")
        print(f"    Affects      : {stops} stop(s), {lines} line(s)")
        if alert.url:
            print(f"    URL          : {alert.url}")
        print()
else:
    print("No current service alerts.")
```

    161 current alert(s):
    
      Route 712 will no longer operate from 3 March
        Last updated : 19/02/2025 13:19
        Affects      : 0 stop(s), 2 line(s)
        URL          : https://transportnsw.info/alerts/details#/ems-47813
    
      Restrictions may apply - confirm when booking
        Last updated : 25/11/2024 10:59
        Affects      : 0 stop(s), 2 line(s)
        URL          : https://transportnsw.info/alerts/details#/ems-195
    
      Lithgow bus disruptions
        Last updated : 26/02/2026 14:36
        Affects      : 0 stop(s), 1 line(s)
        URL          : https://transportnsw.info/alerts/details#/ems-66075
    
      Station Update - Parramatta
        Last updated : 20/02/2026 13:30
        Affects      : 1 stop(s), 18 line(s)
        URL          : https://transportnsw.info/alerts/details#/c8f1b67538aaf404295e35a56affec398cfa2838
    
      Running late
        Last updated : 24/05/2025 22:22
        Affects      : 0 stop(s), 1 line(s)
        URL          : https://transportnsw.info/alerts/details#/5e18016b53e9d923d3366c25cf8be6a40b3893f1
    


## 10 · Find Nearby Stops

`find_nearby()` returns stops/POIs within a given radius of a coordinate.


```python
# Coordinates: Sydney Opera House
lat, lon = -33.8568, 151.2153

nearby = client.find_nearby(lat, lon, radius_m=1000, type_1="STOP")
print(f"Nearby transport stops within 300 m of Sydney Opera House ({lat}, {lon}):\n")
for loc in nearby[:8]:
    modes = ", ".join(TransportMode.from_class(m).name.title() for m in loc.modes) if loc.modes else "—"
    coord = str(loc.coord) if loc.coord else "—"
    print(f"  {loc.name}")
    print(f"    ID       : {loc.id}")
    print(f"    Name     : {loc.name}")
    print(f"    Modes    : {modes}")
    print(f"    Distance : {loc.distance}")
    print(f"    Coord    : {coord}")
    print()
```

    Nearby transport stops within 300 m of Sydney Opera House (-33.8568, 151.2153):
    
      Circular Quay, Sydney
        ID       : 200020
        Name     : Circular Quay, Sydney
        Modes    : Train, Light_Rail, Bus, Ferry
        Distance : 654
        Coord    : Coordinate(lat=-33.861351, lon=151.210813)
    
      Admiralty House, Kirribilli Ave, Kirribilli
        ID       : G206118
        Name     : Admiralty House, Kirribilli Ave, Kirribilli
        Modes    : Bus
        Distance : 695
        Coord    : Coordinate(lat=-33.850928, lon=151.21787)
    
      Olympic Dr before Alfred St, Milsons Point
        ID       : G206143
        Name     : Olympic Dr before Alfred St, Milsons Point
        Modes    : Bus, School_Bus
        Distance : 782
        Coord    : Coordinate(lat=-33.850378, lon=151.21185)
    
      Jeffrey Street Wharf, Kirribilli
        ID       : 206133
        Name     : Jeffrey Street Wharf, Kirribilli
        Modes    : Ferry
        Distance : 792
        Coord    : Coordinate(lat=-33.849755, lon=151.213968)
    
      Walsh Bay Arts Precinct, Hickson Rd, Dawes Point
        ID       : G2000129
        Name     : Walsh Bay Arts Precinct, Hickson Rd, Dawes Point
        Modes    : Bus
        Distance : 804
        Coord    : Coordinate(lat=-33.856042, lon=151.206675)
    
      Kirribilli Ave opp Jeffrey St, Kirribilli
        ID       : G206119
        Name     : Kirribilli Ave opp Jeffrey St, Kirribilli
        Modes    : Bus
        Distance : 822
        Coord    : Coordinate(lat=-33.849404, lon=151.21502)
    
      Milsons Point Wharf, Alfred St Sth, Milsons Point
        ID       : G206120
        Name     : Milsons Point Wharf, Alfred St Sth, Milsons Point
        Modes    : Bus, School_Bus
        Distance : 846
        Coord    : Coordinate(lat=-33.849905, lon=151.211427)
    
      Museum of Sydney, Phillip St, Sydney
        ID       : G200059
        Name     : Museum of Sydney, Phillip St, Sydney
        Modes    : Bus, School_Bus
        Distance : 864
        Coord    : Coordinate(lat=-33.863994, lon=151.211764)
    



```python
# Debug: inspect the raw coord API response to find the correct field names
import json
lat, lon = -33.8568, 151.2153
coord_str = f"{lon:.6f}:{lat:.6f}:EPSG:4326"
raw = client._get("coord", {
    "coord": coord_str,
    "type_1": "STOP",
    "radius_1": 10000,
    "inclFilter": 1,
    "outputFormat": "rapidJSON",
    "coordOutputFormat": "EPSG:4326",
})
locations_raw = raw.get("locations", [])
if locations_raw:
    print("First location raw keys:", list(locations_raw[0].keys()))
    print(json.dumps(locations_raw[0], indent=2))
```

    First location raw keys: ['id', 'isGlobalId', 'name', 'type', 'coord', 'parent', 'productClasses', 'properties', 'disassembledName']
    {
      "id": "200020",
      "isGlobalId": true,
      "name": "undefined, undefined",
      "type": "stop",
      "coord": [
        -33.861351,
        151.210813
      ],
      "parent": {
        "id": "200020",
        "name": "undefined, undefined",
        "type": "locality"
      },
      "productClasses": [
        1,
        4,
        5,
        9
      ],
      "properties": {
        "distance": 654,
        "STOP_GLOBAL_ID": "200020",
        "STOP_NAME_WITH_PLACE": "Circular Quay, Sydney",
        "STOP_MAJOR_MEANS": "2",
        "STOP_MEANS_LIST": "2,4,3,10",
        "STOP_MOT_LIST": "1,4,5,9",
        "stopId": "10101103"
      },
      "disassembledName": "undefined, undefined"
    }


## 11 · Export to Markdown

Run the command below from the project root to **execute** the notebook and write `demo.md` with all code cells and their live output embedded:

```bash
jupyter nbconvert --to markdown --execute demo.ipynb --output demo.md
```

`jupyter` and `nbconvert` are **not** dependencies of `tfnsw-trip-planner`.  
Install them once in your dev environment:

```bash
pip install jupyter nbconvert
```
