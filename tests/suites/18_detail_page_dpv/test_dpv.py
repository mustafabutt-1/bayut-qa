"""§18 Detail page (DPV) — docs/REGRESSION-CHECKLIST.md.

Back/share/favourite presence, the Share button's safety classification (SHARE is
DPV-only — a distinct control from the lead controls covered in 05_leads/test_leads.py,
which are EMAIL/CALL/WHATSAPP, so there's no overlap despite both files exercising the
DPV screen), content-sheet expansion, Property Information / Regulatory Information /
Recommended Properties visibility, and the Activity-Log "marks viewed" cross-check — the
last four ported from appium/tests/test_dpv_navigation.py and test_dpv_marks_viewed.py
(docs/DECISIONS.md D-019). Still not covered: Gallery, TruScan, Virtual tour, chips,
Mortgage Calculator — no located elements for those yet.

Navigating to the DPV itself (open_first_listing -> is_displayed) is intentionally not
its own test here — 15_listing_fat_cards/test_listing_fat_cards.py already covers "tap a
card opens the DPV", and test_back_button_returns_to_results below already opens the DPV
en route to asserting the back button, so a bare "DPV opened" test would assert a strict
subset of what that test already proves.
"""
from __future__ import annotations


def test_back_share_favourite_present(properties_screen):
    dpv = properties_screen.open_first_listing()
    try:
        assert dpv.is_present(resource_id=dpv.BACK)
        assert dpv.is_present(resource_id=dpv.SHARE)
        assert dpv.is_present(resource_id=dpv.FAVOURITE)
    finally:
        dpv.go_back()


def test_share_button_blocked(properties_screen):
    dpv = properties_screen.open_first_listing()
    try:
        dpv.assert_blocked(resource_id=dpv.SHARE)
    finally:
        dpv.go_back()


def test_back_button_returns_to_results(properties_screen):
    dpv = properties_screen.open_first_listing()
    results = dpv.go_back()
    assert results.is_displayed()


def test_content_sheet_and_sections(properties_screen):
    dpv = properties_screen.open_first_listing()
    try:
        dpv.assert_favourite_button_visible()
        dpv.expand_content_sheet()
        dpv.assert_property_information_visible()
        dpv.assert_regulatory_information_soft()
        dpv.assert_recommended_properties_visible()
    finally:
        dpv.go_back()


def test_dpv_marks_viewed_in_activity_log(properties_screen, home_screen):
    price = properties_screen.first_listing_price()
    dpv = properties_screen.open_first_listing()
    assert dpv.is_displayed()
    dpv.go_back()

    more = home_screen.open_more()
    activity_log = more.open_activity_log()
    activity_log.open_viewed_tab()
    assert price is not None, "could not read the listing's price to cross-check"
    activity_log.assert_entry_visible(price)
