"""Main HTTP client for the TfNSW Trip Planner APIs."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")
from urllib.parse import urlencode

import requests
from requests import Response, Session

from .exceptions import APIError, NetworkError
from .models import (
    CyclingProfile,
    Journey,
    Location,
    LocationType,
    ServiceAlert,
    StopEvent,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.transport.nsw.gov.au/v1/tp/"


def _to_sydney(dt: datetime) -> datetime:
    """Ensure a datetime is expressed in Sydney local time.

    Aware datetimes are converted; naive datetimes are assumed to already
    be Sydney local time and are tagged accordingly.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_SYDNEY_TZ)
    return dt.astimezone(_SYDNEY_TZ)

_COMMON_PARAMS: dict[str, str] = {
    "outputFormat": "rapidJSON",
    "coordOutputFormat": "EPSG:4326",
}


class TripPlannerClient:
    """
    Python client for the Transport for NSW Trip Planning APIs.

    Wraps the following endpoints:
      - stop_finder   : Search for stops, POIs and addresses.
      - trip          : Plan a journey between two locations.
      - departure_mon : List upcoming departures from a stop.
      - add_info      : Retrieve service alerts.
      - coord         : Find nearby stops / POIs by coordinate.

    Parameters
    ----------
    api_key : str
        Your TfNSW Open Data API key (passed as the ``Authorization`` header).
    timeout : int
        HTTP request timeout in seconds (default 30).
    session : requests.Session, optional
        Inject a custom ``requests.Session`` (useful for testing).

    Example
    -------
    >>> client = TripPlannerClient(api_key="your_key_here")
    >>> locations = client.find_stop("Circular Quay")
    >>> journeys = client.plan_trip(
    ...     origin_id="10101331",
    ...     destination_id="10102027",
    ... )
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        session: Session | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({"Authorization": f"apikey {api_key}"})

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict:
        """Perform a GET request and return parsed JSON."""
        merged = {**_COMMON_PARAMS, **params}
        url = _BASE_URL + endpoint
        logger.debug("GET %s?%s", url, urlencode(merged))
        try:
            response: Response = self._session.get(url, params=merged, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise NetworkError(f"Connection error: {exc}") from exc
        except requests.Timeout as exc:
            raise NetworkError(f"Request timed out after {self.timeout}s") from exc

        if not response.ok:
            raise APIError(
                f"API error {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise APIError(f"Invalid JSON response: {exc}") from exc

    # ------------------------------------------------------------------
    # Stop Finder API
    # ------------------------------------------------------------------

    def find_stop(
        self,
        query: str,
        location_type: str = "any",
        max_results: int = 10,
        *,
        tfnsw_sf: bool = True,
    ) -> list[Location]:
        """
        Search for stops, POIs and addresses by name.

        Parameters
        ----------
        query : str
            Free-text search term (e.g. ``"Circular Quay"``).
        location_type : str
            Filter by location type. ``"any"`` returns everything;
            ``"stop"`` returns only stops.
        max_results : int
            Maximum number of results to return (default 10).
        tfnsw_sf : bool
            Enable TfNSW-specific filtering (default ``True``).

        Returns
        -------
        list[Location]
            Locations sorted by ``match_quality`` (best first).
        """
        # Always query with type_sf=any — the API silently returns zero results
        # when a specific type is passed for free-text queries. Filter client-side.
        data = self._get(
            "stop_finder",
            {
                "type_sf": "any",
                "name_sf": query,
                "anyMaxSizeHitList": max_results if location_type == "any" else max_results * 5,
                "TfNSWSF": "true" if tfnsw_sf else "false",
                "odvSugMacro": 1,
            },
        )
        locations = [Location.from_dict(loc) for loc in data.get("locations", [])]
        if location_type != "any":
            locations = [l for l in locations if l.type.value == location_type]
        return sorted(locations, key=lambda l: l.match_quality, reverse=True)[:max_results]

    def find_stop_by_id(self, stop_id: str) -> Location | None:
        """
        Look up a stop by its numeric ID.

        Returns ``None`` if no matching stop is found.
        """
        locations = self.find_stop(stop_id, location_type="stop", max_results=1)
        return locations[0] if locations else None

    def best_stop(self, query: str) -> Location | None:
        """
        Return the single best-matching location for *query*.

        Equivalent to ``find_stop(query)[0]`` with ``isBest`` priority.
        """
        locations = self.find_stop(query)
        for loc in locations:
            if loc.is_best:
                return loc
        return locations[0] if locations else None

    # ------------------------------------------------------------------
    # Trip Planner API
    # ------------------------------------------------------------------

    def plan_trip(
        self,
        origin_id: str,
        destination_id: str,
        *,
        when: datetime | None = None,
        arrive_by: bool = False,
        origin_type: str = "stop",
        destination_type: str = "stop",
        realtime: bool = True,
        wheelchair: bool = False,
    ) -> list[Journey]:
        """
        Plan a trip between two locations.

        Parameters
        ----------
        origin_id : str
            Stop ID (or coordinate string) for the origin.
        destination_id : str
            Stop ID (or coordinate string) for the destination.
        when : datetime, optional
            Search date/time. Defaults to now.
        arrive_by : bool
            If ``True`` the time is treated as an *arrival* time instead
            of a departure time.
        origin_type : str
            ``"stop"`` (default) or ``"coord"``.
        destination_type : str
            ``"stop"`` (default) or ``"coord"``.
        realtime : bool
            Include real-time estimates (default ``True``).
        wheelchair : bool
            Only return wheelchair-accessible journeys.

        Returns
        -------
        list[Journey]
        """
        dt = _to_sydney(when or datetime.now(tz=_SYDNEY_TZ))
        params: dict[str, Any] = {
            "depArrMacro": "arr" if arrive_by else "dep",
            "itdDate": dt.strftime("%Y%m%d"),
            "itdTime": dt.strftime("%H%M"),
            "type_origin": origin_type,
            "name_origin": origin_id,
            "type_destination": destination_type,
            "name_destination": destination_id,
            "TfNSWTR": "true" if realtime else "false",
        }
        if wheelchair:
            params["wheelchair"] = "on"

        data = self._get("trip", params)
        return [Journey.from_dict(j) for j in data.get("journeys", [])]

    def plan_trip_from_coordinate(
        self,
        latitude: float,
        longitude: float,
        destination_id: str,
        *,
        when: datetime | None = None,
        arrive_by: bool = False,
        realtime: bool = True,
        wheelchair: bool = False,
    ) -> list[Journey]:
        """
        Plan a trip from the given GPS coordinate to a destination stop.

        Parameters
        ----------
        latitude, longitude : float
            User's current GPS position.
        destination_id : str
            Stop ID of the destination.
        """
        coord_str = f"{longitude:.6f}:{latitude:.6f}:EPSG:4326"
        return self.plan_trip(
            origin_id=coord_str,
            destination_id=destination_id,
            origin_type="coord",
            when=when,
            arrive_by=arrive_by,
            realtime=realtime,
            wheelchair=wheelchair,
        )

    def plan_cycling_trip(
        self,
        origin_id: str,
        destination_id: str,
        *,
        profile: CyclingProfile = CyclingProfile.MODERATE,
        when: datetime | None = None,
        bike_only: bool = True,
        max_time_minutes: int = 240,
        cycle_speed: int = 16,
    ) -> list[Journey]:
        """
        Plan a cycling trip (optionally combined with transit).

        Parameters
        ----------
        origin_id, destination_id : str
            Stop IDs for origin and destination.
        profile : CyclingProfile
            One of ``EASIER``, ``MODERATE``, ``MORE_DIRECT``.
        when : datetime, optional
            Departure time (defaults to now).
        bike_only : bool
            ``True`` for a bike-only trip; ``False`` allows the bike
            to be used as one leg of a multi-modal trip.
        max_time_minutes : int
            Maximum trip duration in minutes (default 240).
        cycle_speed : int
            Cycling speed in km/h (default 16).
        """
        elev_fac_map = {
            CyclingProfile.EASIER: 0,
            CyclingProfile.MODERATE: 50,
            CyclingProfile.MORE_DIRECT: 100,
        }
        dt = _to_sydney(when or datetime.now(tz=_SYDNEY_TZ))
        params: dict[str, Any] = {
            "depArrMacro": "dep",
            "itdDate": dt.strftime("%Y%m%d"),
            "itdTime": dt.strftime("%H%M"),
            "type_origin": "stop",
            "name_origin": origin_id,
            "type_destination": "stop",
            "name_destination": destination_id,
            "TfNSWTR": "true",
            "cycleSpeed": cycle_speed,
            "computeMonomodalTripBicycle": 1 if bike_only else 0,
            "maxTimeBicycle": max_time_minutes,
            "onlyITBicycle": 1,
            "useElevationData": 1,
            "bikeProfSpeed": profile.value,
            "elevFac": elev_fac_map[profile],
        }
        data = self._get("trip", params)
        return [Journey.from_dict(j) for j in data.get("journeys", [])]

    # ------------------------------------------------------------------
    # Departure API
    # ------------------------------------------------------------------

    def get_departures(
        self,
        stop_id: str,
        *,
        when: datetime | None = None,
        platform_id: str | None = None,
        realtime: bool = True,
    ) -> list[StopEvent]:
        """
        List upcoming departures from a stop or platform.

        Parameters
        ----------
        stop_id : str
            The stop or platform ID.
        when : datetime, optional
            Base departure time (defaults to now).
        platform_id : str, optional
            Narrow results to a specific platform ID.
        realtime : bool
            Include real-time data (default ``True``).

        Returns
        -------
        list[StopEvent]
        """
        dt = _to_sydney(when or datetime.now(tz=_SYDNEY_TZ))
        params: dict[str, Any] = {
            "mode": "direct",
            "type_dm": "stop",
            "name_dm": stop_id,
            "depArrMacro": "dep",
            "itdDate": dt.strftime("%Y%m%d"),
            "itdTime": dt.strftime("%H%M"),
            "TfNSWDM": "true" if realtime else "false",
        }
        if platform_id:
            params["name_dm"] = platform_id
            params["nameKey_dm"] = "$USEPOINT$"

        data = self._get("departure_mon", params)
        return [StopEvent.from_dict(e) for e in data.get("stopEvents", [])]

    # ------------------------------------------------------------------
    # Service Alert API
    # ------------------------------------------------------------------

    def get_alerts(
        self,
        *,
        when: datetime | None = None,
        stop_id: str | None = None,
        current_only: bool = True,
    ) -> list[ServiceAlert]:
        """
        Retrieve service alerts.

        Parameters
        ----------
        when : datetime, optional
            Filter by this date (defaults to today).
        stop_id : str, optional
            Only return alerts relevant to this stop.
        current_only : bool
            Exclude historical/inactive alerts (default ``True``).

        Returns
        -------
        list[ServiceAlert]
        """
        dt = _to_sydney(when or datetime.now(tz=_SYDNEY_TZ))
        params: dict[str, Any] = {
            "filterDateValid": dt.strftime("%d-%m-%Y"),
        }
        if current_only:
            params["filterPublicationStatus"] = "current"
        if stop_id:
            params["itdLPxx_selStop"] = stop_id

        data = self._get("add_info", params)
        infos = data.get("infos", {})
        alerts_raw = infos.get("current", []) if current_only else (
            infos.get("current", []) + infos.get("previous", [])
        )
        return [ServiceAlert.from_dict(a) for a in alerts_raw]

    # ------------------------------------------------------------------
    # Coordinate Request API
    # ------------------------------------------------------------------

    def find_nearby(
        self,
        latitude: float,
        longitude: float,
        *,
        radius_m: int = 500,
        type_1: str = "GIS_POINT",
        draw_class: int | None = None,
    ) -> list[Location]:
        """
        Find stops, POIs or Opal resellers near a coordinate.

        Parameters
        ----------
        latitude, longitude : float
            Centre of the search area.
        radius_m : int
            Search radius in metres (default 500).
        type_1 : str
            Location type filter (default ``"GIS_POINT"``).
        draw_class : int, optional
            Draw class filter. Use ``74`` for Opal resellers.

        Returns
        -------
        list[Location]
        """
        coord_str = f"{longitude:.6f}:{latitude:.6f}:EPSG:4326"
        params: dict[str, Any] = {
            "coord": coord_str,
            "type_1": type_1,
            "radius_1": radius_m,
            "inclFilter": 1,
        }
        if draw_class is not None:
            params["inclDrawClasses_1"] = draw_class

        data = self._get("coord", params)
        return [Location.from_dict(loc) for loc in data.get("locations", [])]

    def find_opal_resellers(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 1000,
    ) -> list[Location]:
        """Find Opal ticket resellers near *latitude*, *longitude*."""
        return self.find_nearby(
            latitude,
            longitude,
            radius_m=radius_m,
            draw_class=74,
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "TripPlannerClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"TripPlannerClient(base_url={_BASE_URL!r})"
