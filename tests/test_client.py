"""Client behaviour against a fake HTTP session: params, parsing, errors, retries."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import requests

from tfnsw_trip_planner import (
    APIError,
    NetworkError,
    RateLimitError,
    TransportMode,
    TripPlannerClient,
    TripPlannerError,
)
from tfnsw_trip_planner import client as client_module

SYDNEY = ZoneInfo("Australia/Sydney")


class FakeResponse:
    def __init__(
        self,
        payload: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        text: str | None = None,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text if text is not None else repr(payload)
        self.content = b""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """Replays queued responses (or raises queued exceptions) and records calls."""

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self.headers: dict[str, str] = {}
        self.queue = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: Any = None) -> Any:
        self.calls.append({"url": url, "params": params or {}, "timeout": timeout})
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self) -> None:
        pass

    @property
    def params(self) -> dict[str, Any]:
        return self.calls[-1]["params"]


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Capture retry sleeps instead of waiting."""
    recorded: list[float] = []
    monkeypatch.setattr(client_module.time, "sleep", recorded.append)
    return recorded


def make_client(*responses: FakeResponse | Exception, **kwargs: Any) -> TripPlannerClient:
    return TripPlannerClient(api_key="test-key", session=FakeSession(*responses), **kwargs)


def session_of(client: TripPlannerClient) -> FakeSession:
    return client._session  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Requests the client builds
# ---------------------------------------------------------------------------


class TestRequests:
    def test_auth_header_is_set(self):
        c = make_client()
        assert session_of(c).headers["Authorization"] == "apikey test-key"

    def test_common_params_and_endpoint(self):
        c = make_client(FakeResponse({"locations": []}))
        c.find_stop("Central")
        call = session_of(c).calls[-1]
        assert call["url"] == "https://api.transport.nsw.gov.au/v1/tp/stop_finder"
        assert call["params"]["outputFormat"] == "rapidJSON"
        assert call["params"]["coordOutputFormat"] == "EPSG:4326"
        assert call["params"]["name_sf"] == "Central"
        assert call["timeout"] == 30

    def test_plan_trip_params(self):
        c = make_client(FakeResponse({"journeys": []}))
        when = datetime(2026, 3, 5, 8, 7, tzinfo=SYDNEY)
        c.plan_trip("A", "B", when=when, arrive_by=True, wheelchair=True, realtime=False)
        p = session_of(c).params
        assert p["depArrMacro"] == "arr"
        assert (p["itdDate"], p["itdTime"]) == ("20260305", "0807")
        assert (p["name_origin"], p["name_destination"]) == ("A", "B")
        assert p["wheelchair"] == "on"
        assert p["TfNSWTR"] == "false"

    def test_aware_datetimes_are_converted_to_sydney(self):
        c = make_client(FakeResponse({"journeys": []}))
        c.plan_trip("A", "B", when=datetime(2026, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC")))
        # 00:00 UTC on 1 Jan is 11:00 AEDT.
        assert (session_of(c).params["itdDate"], session_of(c).params["itdTime"]) == (
            "20260101",
            "1100",
        )

    def test_plan_trip_from_coordinate_sends_lon_first(self):
        c = make_client(FakeResponse({"journeys": []}))
        c.plan_trip_from_coordinate(-33.8688, 151.2093, "200060")
        p = session_of(c).params
        assert p["type_origin"] == "coord"
        assert p["name_origin"] == "151.209300:-33.868800:EPSG:4326"

    def test_get_departures_platform(self):
        c = make_client(FakeResponse({"stopEvents": [{}]}))
        c.get_departures("200060", platform_id="2000336")
        p = session_of(c).params
        assert p["name_dm"] == "2000336"
        assert p["nameKey_dm"] == "$USEPOINT$"

    def test_find_nearby_draw_class(self):
        c = make_client(FakeResponse({"locations": []}))
        c.find_nearby(-33.0, 151.0, radius_m=250, draw_class=74)
        p = session_of(c).params
        assert p["radius_1"] == 250
        assert p["inclDrawClasses_1"] == 74


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------


class TestFindStop:
    def test_filters_by_type_and_sorts_by_match_quality(self):
        c = make_client(
            FakeResponse(
                {
                    "locations": [
                        {"id": "1", "name": "Low", "type": "stop", "matchQuality": 10},
                        {"id": "2", "name": "Poi", "type": "poi", "matchQuality": 999},
                        {"id": "3", "name": "High", "type": "stop", "matchQuality": 900},
                    ]
                }
            )
        )
        result = c.find_stop("x", location_type="stop")
        assert [loc.id for loc in result] == ["3", "1"]
        # Over-fetch so client-side type filtering still fills max_results.
        assert session_of(c).params["anyMaxSizeHitList"] == 50

    def test_best_stop_prefers_is_best(self):
        c = make_client(
            FakeResponse(
                {
                    "locations": [
                        {"id": "1", "type": "stop", "matchQuality": 999},
                        {"id": "2", "type": "stop", "matchQuality": 1, "isBest": True},
                    ]
                }
            )
        )
        best = c.best_stop("x")
        assert best is not None and best.id == "2"

    def test_error_system_message_alongside_results_is_ignored(self):
        # Real behaviour: stop_finder sends {"type": "error", "code": -8011}
        # even when it returns matches.
        c = make_client(
            FakeResponse(
                {
                    "systemMessages": [{"type": "error", "code": -8011, "text": ""}],
                    "locations": [{"id": "1", "type": "stop"}],
                }
            )
        )
        assert len(c.find_stop("Central")) == 1

    def test_null_locations(self):
        c = make_client(FakeResponse({"locations": None}))
        assert c.find_stop("x") == []


class TestSystemMessageErrors:
    def test_invalid_stop_raises(self):
        body = {
            "systemMessages": [
                {"type": "error", "module": "BROKER", "code": -2000, "text": "origin: stop invalid"}
            ]
        }
        c = make_client(FakeResponse(body))
        with pytest.raises(APIError, match="origin: stop invalid") as exc_info:
            c.plan_trip("999999999", "200060")
        assert exc_info.value.code == -2000
        assert exc_info.value.status_code == 200

    def test_no_route_warning_returns_empty_list(self):
        # "No trip found" is a warning (code -4000), not an error.
        body = {"systemMessages": [{"type": "warning", "code": -4000, "text": "itp"}]}
        c = make_client(FakeResponse(body))
        assert c.plan_trip("A", "B") == []

    def test_errors_ignored_when_results_present(self):
        body = {
            "systemMessages": [{"type": "error", "code": -1, "text": "x"}],
            "journeys": [{"legs": []}],
        }
        c = make_client(FakeResponse(body))
        assert len(c.plan_trip("A", "B")) == 1

    def test_departures_invalid_date_raises(self):
        body = {
            "systemMessages": [{"type": "error", "code": -4001, "text": "invalid date"}],
            "locations": [{}],
        }
        c = make_client(FakeResponse(body))
        with pytest.raises(APIError, match="invalid date"):
            c.get_departures("200060")

    def test_error_without_text_uses_code(self):
        body = {"systemMessages": [{"type": "error", "code": -303}]}
        c = make_client(FakeResponse(body))
        with pytest.raises(APIError, match="code -303"):
            c.plan_cycling_trip("A", "B")


class TestAlerts:
    BODY = {
        "infos": {
            "current": [{"subtitle": "now"}],
            "historic": [{"subtitle": "then"}],
            "affected": {},
        }
    }

    def test_current_only(self):
        c = make_client(FakeResponse(self.BODY))
        assert [a.subtitle for a in c.get_alerts()] == ["now"]
        assert session_of(c).params["filterPublicationStatus"] == "current"

    def test_include_historic(self):
        c = make_client(FakeResponse(self.BODY))
        assert [a.subtitle for a in c.get_alerts(current_only=False)] == ["now", "then"]
        assert "filterPublicationStatus" not in session_of(c).params

    def test_stop_and_date_filters(self):
        c = make_client(FakeResponse({"infos": None}))
        assert c.get_alerts(when=datetime(2026, 2, 3, 12, tzinfo=SYDNEY), stop_id="200060") == []
        p = session_of(c).params
        assert p["filterDateValid"] == "03-02-2026"
        assert p["itdLPxx_selStop"] == "200060"


class TestBadResponses:
    def test_http_error_raises_api_error(self):
        c = make_client(FakeResponse(None, status_code=401, text="unauthorised"))
        with pytest.raises(APIError) as exc_info:
            c.find_stop("x")
        assert exc_info.value.status_code == 401

    def test_invalid_json(self):
        c = make_client(FakeResponse(ValueError("bad json")))
        with pytest.raises(APIError, match="Invalid JSON"):
            c.find_stop("x")

    def test_non_object_json(self):
        c = make_client(FakeResponse(["not", "an", "object"]))
        with pytest.raises(APIError, match="expected a JSON object"):
            c.find_stop("x")

    def test_null_nested_fields_do_not_crash(self):
        body = {"journeys": [{"legs": [{"origin": None, "destination": None, "coords": None}]}]}
        c = make_client(FakeResponse(body))
        (journey,) = c.plan_trip("A", "B")
        assert journey.legs[0].mode is TransportMode.UNKNOWN


# ---------------------------------------------------------------------------
# Network failures and retries
# ---------------------------------------------------------------------------


class TestNetworkErrors:
    @pytest.mark.parametrize(
        "exc, message",
        [
            (requests.ConnectionError("refused"), "Connection error"),
            (requests.Timeout("slow"), "timed out"),
            (requests.exceptions.ChunkedEncodingError("broken"), "Request failed"),
        ],
    )
    def test_requests_exceptions_become_network_error(self, sleeps, exc, message):
        c = make_client(exc, max_retries=0)
        with pytest.raises(NetworkError, match=message) as exc_info:
            c.find_stop("x")
        assert isinstance(exc_info.value, TripPlannerError)
        assert exc_info.value.__cause__ is exc

    def test_network_error_is_retried(self, sleeps):
        c = make_client(requests.ConnectionError("blip"), FakeResponse({"locations": []}))
        assert c.find_stop("x") == []
        assert sleeps == [0.5]

    def test_gives_up_after_max_retries(self, sleeps):
        errors = [requests.ConnectionError("down")] * 3
        c = make_client(*errors, max_retries=2)
        with pytest.raises(NetworkError):
            c.find_stop("x")
        assert len(session_of(c).calls) == 3
        assert sleeps == [0.5, 1.0]


class TestRetries:
    @pytest.mark.parametrize("status", [429, 502, 503, 504])
    def test_transient_statuses_are_retried(self, sleeps, status):
        c = make_client(FakeResponse(None, status_code=status), FakeResponse({"locations": []}))
        assert c.find_stop("x") == []
        assert len(session_of(c).calls) == 2

    def test_other_errors_are_not_retried(self, sleeps):
        c = make_client(FakeResponse(None, status_code=500))
        with pytest.raises(APIError):
            c.find_stop("x")
        assert sleeps == []

    def test_retry_after_seconds_is_honoured(self, sleeps):
        c = make_client(
            FakeResponse(None, status_code=429, headers={"Retry-After": "3"}),
            FakeResponse({"locations": []}),
        )
        c.find_stop("x")
        assert sleeps == [3.0]

    def test_rate_limit_error_after_retries(self, sleeps):
        responses = [FakeResponse(None, status_code=429, headers={"Retry-After": "1"})] * 3
        c = make_client(*responses)
        with pytest.raises(RateLimitError) as exc_info:
            c.find_stop("x")
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 1.0
        assert isinstance(exc_info.value, APIError)

    def test_long_retry_after_raises_immediately(self, sleeps):
        # e.g. a daily quota reset: don't block the caller for an hour.
        c = make_client(FakeResponse(None, status_code=429, headers={"Retry-After": "3600"}))
        with pytest.raises(RateLimitError) as exc_info:
            c.find_stop("x")
        assert exc_info.value.retry_after == 3600.0
        assert sleeps == []

    def test_http_date_retry_after(self, sleeps):
        c = make_client(
            FakeResponse(
                None, status_code=503, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}
            ),
            FakeResponse({"locations": []}),
        )
        c.find_stop("x")
        assert sleeps == [0.0]  # a date in the past means "retry now"

    def test_retries_can_be_disabled(self, sleeps):
        c = make_client(FakeResponse(None, status_code=503), max_retries=0)
        with pytest.raises(APIError):
            c.find_stop("x")
        assert len(session_of(c).calls) == 1

    def test_negative_max_retries_rejected(self):
        with pytest.raises(ValueError):
            TripPlannerClient(api_key="k", session=FakeSession(), max_retries=-1)


class TestLifecycle:
    def test_context_manager_closes_session(self):
        closed = []
        session = FakeSession()
        session.close = lambda: closed.append(True)  # type: ignore[method-assign]
        with TripPlannerClient(api_key="k", session=session) as c:
            assert "TripPlannerClient" in repr(c)
        assert closed == [True]
