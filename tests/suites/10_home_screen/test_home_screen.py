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
    """All five bottom-nav destinations exist.

    Resolved by resource-id, not by the content-desc these used to use: a content-desc
    is localized, so those locators would stop resolving in ar/ru/zh — three of the
    app's four shipped locales. Home is included now that it is addressable by id;
    it was previously unreachable by label because the selected tab exposes no
    clickable content-desc.
    """
    for name in ("NAV_HOME", "NAV_PROPERTIES", "NAV_TRANSACTIONS",
                 "NAV_HOME_VALUE", "NAV_MORE"):
        resource_id = getattr(home_screen, name)
        assert home_screen.is_present(resource_id=resource_id), (
            f"bottom-nav {name} ({resource_id}) not present on Home"
        )


def test_bottom_nav_properties_opens_results(home_screen):
    results = home_screen.open_properties()
    assert results.is_displayed()
