from tfnsw_trip_planner import TripPlannerClient
from dotenv import load_dotenv
import os

load_dotenv()

TRANSPORT_NSW_API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")

print(f"API Key: {TRANSPORT_NSW_API_KEY=}")

client = TripPlannerClient(api_key=TRANSPORT_NSW_API_KEY)

locations = client.find_stop("Fermo")
for loc in locations:
    print(loc.name)
    print(loc.id)
    print(loc.coord)

# # Get the best single match
# best = client.best_stop("Domestic Airport")
# print(best.id, best.name)

# journeys = client.plan_trip(
#     origin_id="G2233133",       # Domestic Airport Station
#     destination_id="10102027",  # Manly Wharf
# )

# for journey in journeys:
#     print(journey)
#     # Journey(legs=3, duration=61min, summary='Train → Walk → Bus')

#     print(f"  Depart : {journey.departure_time}")
#     print(f"  Arrive : {journey.arrival_time}")
#     print(f"  Route  : {journey.summary}")

#     for leg in journey.legs:
#         #print(dir(leg))
#         print(f"    {leg.mode} {leg.origin} → {leg.destination} ({leg.duration}) {leg.transportation.number}")

#     fare = journey.fare_summary
#     if fare:
#         print(f"  Cost   : ${fare.price_total:.2f} ({fare.status.value})")

departures = client.get_departures("2233133")  # Domestic Airport

for event in departures[:2]:
    mins = event.minutes_until_departure
    rt   = "⚡" if event.is_realtime else "🕐"
    print(f"{rt} {mins:>3}m  {event.departure_time} {event.transportation.number:>8}  → {event.transportation.destination_name}")