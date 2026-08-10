"""§10 Home screen — docs/REGRESSION-CHECKLIST.md.

Partial coverage only. The checklist asks to verify Header, TruBroker banner, Seller
leads banner, Banners (TruEstimate/BayutGPT/Dubai Transactions/Search 2.0), Continue
last search, Saved Searches, Favourites, Popular, Lookup Nearby, Blogs, and Bottom Nav.
Only the header section-tabs, the Buy/Rent + search row, and bottom-nav presence are
locator-confirmed so far — the rest needs another crawl pass (they're visible in
screenshots from this session but weren't individually captured in
context/element-inventory.json).
"""
from __future__ import annotations


def test_header_section_tabs_present(home_screen):
    assert home_screen.is_present(resource_id=home_screen.PROPERTIES_TAB)
    assert home_screen.is_present(resource_id=home_screen.NEW_PROJECTS_TAB)
    assert home_screen.is_present(resource_id=home_screen.TRANSACTIONS_TAB)
    assert home_screen.is_present(resource_id=home_screen.AGENTS_TAB)


def test_buy_rent_and_search_bar_present(home_screen):
    assert home_screen.is_present(resource_id=home_screen.BUY_RADIO)
    assert home_screen.is_present(resource_id=home_screen.RENT_RADIO)
    assert home_screen.is_present(resource_id=home_screen.SEARCH_BAR)


def test_bottom_nav_present(home_screen):
    assert home_screen.is_present(accessibility_id=home_screen.NAV_PROPERTIES)
    assert home_screen.is_present(accessibility_id=home_screen.NAV_TRANSACTIONS)
    assert home_screen.is_present(accessibility_id=home_screen.NAV_HOME_VALUE)
    assert home_screen.is_present(accessibility_id=home_screen.NAV_MORE)


def test_bottom_nav_properties_opens_results(home_screen):
    results = home_screen.open_properties()
    assert results.is_displayed()
