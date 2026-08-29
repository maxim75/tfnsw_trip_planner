"""Unit tests for the Location model."""
from tfnsw_trip_planner.models.enums import LocationType
from tfnsw_trip_planner.models.location import Location


# A trimmed but faithful stop_finder response entry. The name is carried at the
# top level here; there is no "properties" key at all.
STOP_FINDER_ENTRY = {
    "id": "streetID:1500000002::95301001:-1:Circular Quay:Sydney",
    "name": "Circular Quay, Sydney",
    "disassembledName": "Circular Quay",
    "type": "street",
    "matchQuality": 250,
    "isBest": False,
    "coord": [-33.861353, 151.210760],
}

# The coord API is sparse at the top level and supplies the name in properties.
COORD_ENTRY = {
    "properties": {
        "STOP_GLOBAL_ID": "200020",
        "STOP_NAME_WITH_PLACE": "Sydney, Circular Quay",
        "STOP_MOT_LIST": "1,4,5,9",
        "distance": "120",
    },
    "type": "stop",
}


class TestLocationName:
    def test_stop_finder_name_is_read_from_the_top_level(self):
        # Regression: the name was previously read only from
        # properties.STOP_NAME_WITH_PLACE, so every stop_finder result — from
        # find_stop, best_stop and find_stop_by_id — came back with name="".
        location = Location.from_dict(STOP_FINDER_ENTRY)

        assert location.name == "Circular Quay, Sydney"

    def test_coord_api_name_still_comes_from_properties(self):
        location = Location.from_dict(COORD_ENTRY)

        assert location.name == "Sydney, Circular Quay"

    def test_top_level_name_wins_over_properties(self):
        location = Location.from_dict(
            {"name": "Top Level", "properties": {"STOP_NAME_WITH_PLACE": "From Properties"}}
        )

        assert location.name == "Top Level"

    def test_disassembled_name_is_the_last_resort(self):
        location = Location.from_dict({"disassembledName": "Circular Quay"})

        assert location.name == "Circular Quay"

    def test_missing_name_is_an_empty_string_not_none(self):
        location = Location.from_dict({"id": "200020"})

        assert location.name == ""


class TestLocationFromDict:
    def test_stop_finder_entry_parses_fully(self):
        location = Location.from_dict(STOP_FINDER_ENTRY)

        assert location.id == STOP_FINDER_ENTRY["id"]
        assert location.type is LocationType.STREET
        assert location.match_quality == 250
        assert location.is_best is False
        assert location.coord is not None

    def test_coord_entry_falls_back_to_properties(self):
        location = Location.from_dict(COORD_ENTRY)

        assert location.id == "200020"
        assert location.modes == [1, 4, 5, 9]
        assert location.distance == 120

    def test_unknown_type_does_not_raise(self):
        assert Location.from_dict({"type": "nonsense"}).type is LocationType.UNKNOWN
