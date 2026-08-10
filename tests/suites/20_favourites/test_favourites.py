"""§20 Favourites — docs/REGRESSION-CHECKLIST.md.

Ported from appium/tests/test_favourite_listing.py (docs/DECISIONS.md D-019).
favourite_cb matches ALLOW-NAV-TABS ("favou?rites?") in the shared policy — same
non-destructive, reversible class as a Save/heart toggle generally, unlike
"Remove from Favourites" which the app-cartographer spec calls out as its own,
separately-blocked action. Goes through the normal safe_tap() gate; no consequential
override needed here.
"""
from __future__ import annotations


def test_favourite_listing_appears_in_favourites(properties_screen, home_screen):
    properties_screen.favourite_nth_listing(0)

    more = home_screen.open_more()
    favourites = more.open_favourites()
    assert favourites.is_displayed()
    favourites.wait_for_first_card()
