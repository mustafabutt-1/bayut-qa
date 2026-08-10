"""§13 Location screen — docs/REGRESSION-CHECKLIST.md.

Covers: the picker opens from "Select location", shows all 8 emirates in Popular
Locations, and closes back to results. The checklist's 17 location-level restriction
rules (which screens allow which location depth) are explicitly out of scope — those
are behavioural rules that need PROBE mode against each of the 17 entry points listed
in the checklist, not a single structural screen capture.
"""
from __future__ import annotations


def test_select_location_opens_picker(properties_screen):
    picker = properties_screen.open_location_picker()
    try:
        assert picker.is_displayed()
    finally:
        results = picker.close()
        assert results.is_displayed()


def test_popular_locations_shows_all_emirates(properties_screen):
    picker = properties_screen.open_location_picker()
    try:
        for emirate in picker.POPULAR_LOCATIONS:
            assert picker.option_present(picker.POPULAR_LOCATION_CHIP, emirate), (
                f"expected emirate {emirate!r} in Popular Locations"
            )
        assert len(picker.POPULAR_LOCATIONS) == 8, (
            "checklist §13 requires exactly 8 emirates in Popular Locations"
        )
    finally:
        picker.close()


def test_reset_and_done_controls_present(properties_screen):
    picker = properties_screen.open_location_picker()
    try:
        assert picker.is_present(resource_id=picker.RESET)
        assert picker.is_present(resource_id=picker.DONE)
    finally:
        picker.close()
