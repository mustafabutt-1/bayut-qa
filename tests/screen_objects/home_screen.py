"""Home screen — OBSERVED 2026-08-10, build 15.7.2 (1272), en-GB.

Covers only the elements actually confirmed by the live crawl: the bottom nav, the
header section-tab bar, and the Buy/Rent + search row. The remaining sections listed in
docs/REGRESSION-CHECKLIST.md #10 (TruBroker banner, Seller leads banner, Recent
Searches, Saved Searches, Favourites, Popular, Lookup Nearby, Blogs) have not been
individually located yet — see docs/PROJECT-STATE.md for what's still open.
"""
from __future__ import annotations

from .base import BaseScreen
from .properties_results_screen import PropertiesResultsScreen


class HomeScreen(BaseScreen):
    PROPERTIES_TAB = "com.bayut.bayutapp:id/properties_tab"       # header segmented tab
    NEW_PROJECTS_TAB = "com.bayut.bayutapp:id/new_projects_tab"    # header segmented tab
    TRANSACTIONS_TAB = "com.bayut.bayutapp:id/transactions_tab"    # header segmented tab
    AGENTS_TAB = "com.bayut.bayutapp:id/agents_tab"                # header segmented tab
    BUY_RADIO = "com.bayut.bayutapp:id/buy_rb"
    RENT_RADIO = "com.bayut.bayutapp:id/rent_rb"
    SEARCH_BAR = "com.bayut.bayutapp:id/text_search"

    # Bottom nav — accessibility ids, distinct elements from the header tabs above,
    # even where the label text coincides (e.g. "Properties" exists as both).
    NAV_PROPERTIES = "Properties"
    NAV_TRANSACTIONS = "Transactions"
    NAV_HOME_VALUE = "Home Value"
    NAV_MORE = "More"

    def is_displayed(self, timeout: int = 3) -> bool:
        return self.is_present(resource_id=self.PROPERTIES_TAB, timeout=timeout)

    def open_properties(self) -> PropertiesResultsScreen:
        """Bottom-nav Properties icon — real navigation, distinct from the header tab
        of the same name. Idempotent: safe to call even if already on Properties."""
        self.safe_tap(accessibility_id=self.NAV_PROPERTIES)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)

    def open_more(self):
        from .more_screen import MoreScreen
        self.safe_tap(accessibility_id=self.NAV_MORE)
        return MoreScreen(self.driver, self.safety_policy, self.timeout)

    def open_location_search(self):
        """Home's own search bar — a second, independent entry point into location
        selection + Filters, distinct from tapping bottom-nav Properties then "Select
        location" on the results screen. Ported from appium/pages/search_filters.py."""
        from .location_picker_screen import LocationPickerScreen
        self.safe_tap(resource_id=self.SEARCH_BAR)
        return LocationPickerScreen(self.driver, self.safety_policy, self.timeout)
