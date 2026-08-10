"""§15 Listing fat cards — docs/REGRESSION-CHECKLIST.md.

Covers only "tapping a card opens the listing" — the checklist's fuller list (badges,
image-swipe gallery, Favourite heart, Viewed/Contacted state, "View more photos" after
5 images) needs individually-located sub-elements that a structural crawl at this scroll
position didn't surface. Favourite-heart interaction is deliberately not exercised here:
it's a gray area on the no-create constraint this session ran under (writes a favourite
record to the account) — see the open question logged in this session's history.
"""
from __future__ import annotations


def test_tapping_card_opens_listing_detail(properties_screen):
    dpv = properties_screen.open_first_listing()
    try:
        assert dpv.is_displayed()
    finally:
        results = dpv.go_back()
        assert results.is_displayed()


def test_favourite_checkbox_present_but_not_tapped(properties_screen):
    """Existence check only — see module docstring for why this stops short of tapping."""
    assert properties_screen.is_present(resource_id=properties_screen.FAVOURITE_CHECKBOX)
