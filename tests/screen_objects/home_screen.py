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

    # Bottom nav — resource-ids, OBSERVED 2026-08-10 build 15.7.2 (1272).
    #
    # These were previously accessibility ids ("Properties", "More", ...). A
    # content-desc is a *localized* string — it is what TalkBack reads aloud — so those
    # locators silently stop resolving the moment the device is in Arabic, Russian or
    # Chinese, which are three of the app's four shipped locales. Resource-ids are
    # compile-time names and identical in every locale and on every device.
    #
    # Note the id/label mismatch: the Properties tab is `bottom_nav_search_id` and the
    # TruEstimate tab is `bottom_nav_truestimate_id` while its visible label reads
    # "Home Value" — another reason not to locate these by what they say.
    NAV_HOME = "com.bayut.bayutapp:id/bottom_nav_home_id"
    NAV_PROPERTIES = "com.bayut.bayutapp:id/bottom_nav_search_id"
    NAV_TRANSACTIONS = "com.bayut.bayutapp:id/bottom_nav_transactions_id"
    NAV_HOME_VALUE = "com.bayut.bayutapp:id/bottom_nav_truestimate_id"
    NAV_MORE = "com.bayut.bayutapp:id/bottom_nav_more_id"

    # --- §10 Home screen sections / banners --------------------------------
    # OBSERVED 2026-08-10, build 15.7.2 (1272), signed out, en-GB, across 12 scrolled
    # dumps of Home. All resource-ids — no text locators, so these hold in ar/ru/zh.
    #
    # Note `cl_trubroker_container` appears on BOTH Home and the LPV; it is the same
    # component reused, which is why §16's LPV widget test and this one can share it.
    TRUBROKER_BANNER = "com.bayut.bayutapp:id/cl_trubroker_container"
    # The container itself is NOT clickable — its child image and badge are. Presence
    # checks use the container; the tap must target the child, or safe_tap finds an
    # unclickable element and the tap goes nowhere.
    TRUBROKER_BANNER_TAP = "com.bayut.bayutapp:id/fl_trubroker_image"
    TRUESTIMATE_BANNER = "com.bayut.bayutapp:id/iv_banner"
    RECENT_SEARCHES_TITLE = "com.bayut.bayutapp:id/tv_home_recent_searches"
    RECENT_SEARCHES_LIST = "com.bayut.bayutapp:id/rv_home_recent_searches"
    POPULAR_ROW_TITLE = "com.bayut.bayutapp:id/homeScreenRowTitle"
    POPULAR_LOCATIONS_LIST = "com.bayut.bayutapp:id/rvPopularLocations"
    BLOG_SECTION_TITLE = "com.bayut.bayutapp:id/tv_blog_section_title"
    BLOG_LIST = "com.bayut.bayutapp:id/rv_blog_items"

    #: Documented Home sections that have a stable id. Absent ids are UNRESOLVED rather
    #: than guessed — see unresolved_sections().
    SECTION_IDS: dict[str, str | None] = {
        "TruBroker banner": TRUBROKER_BANNER,
        "TruEstimate banner": TRUESTIMATE_BANNER,
        "Recent Searches": RECENT_SEARCHES_TITLE,
        "Popular section": POPULAR_LOCATIONS_LIST,
        "Blogs": BLOG_LIST,
        "BayutGPT banner": None,           # UNRESOLVED — never observed on Home
        "Dubai Transactions banner": None,  # UNRESOLVED — never observed on Home
        "Seller leads banner": None,        # UNRESOLVED — never observed (agent-gated?)
        "Search 2.0 banner": None,          # UNRESOLVED — never observed
        "Lookup Nearby Locations": None,    # UNRESOLVED — needs location permission
    }

    def unresolved_sections(self) -> list[str]:
        return [n for n, rid in self.SECTION_IDS.items() if not rid]

    def sections_present(self, max_swipes: int = 12) -> dict[str, bool]:
        """Scroll Home top-to-bottom, recording which known sections were seen.

        Located purely by resource-id. A section with no known id is excluded here and
        reported separately by `unresolved_sections()`, so "not checkable" never gets
        silently reported as "not present".
        """
        known = {rid: name for name, rid in self.SECTION_IDS.items() if rid}
        found = {name: False for name in known.values()}
        # Start from the top, or any section above the current scroll position is
        # reported missing when it is merely already scrolled past.
        self.swipe_down_to_top()
        for _ in range(max_swipes):
            for el in self.current_elements():
                name = known.get(el.resource_id)
                if name:
                    found[name] = True
            if all(found.values()):
                break
            self.swipe_up()
        return found

    def is_displayed(self, timeout: int = 3) -> bool:
        return self.is_present(resource_id=self.PROPERTIES_TAB, timeout=timeout)

    def open_properties(self) -> PropertiesResultsScreen:
        """Bottom-nav Properties icon — real navigation, distinct from the header tab
        of the same name. Idempotent: safe to call even if already on Properties."""
        self.safe_tap(resource_id=self.NAV_PROPERTIES)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)

    def open_more(self):
        from .more_screen import MoreScreen
        self.safe_tap(resource_id=self.NAV_MORE)
        return MoreScreen(self.driver, self.safety_policy, self.timeout)

    def open_location_search(self):
        """Home's own search bar — a second, independent entry point into location
        selection + Filters, distinct from tapping bottom-nav Properties then "Select
        location" on the results screen. Ported from appium/pages/search_filters.py."""
        from .location_picker_screen import LocationPickerScreen
        self.safe_tap(resource_id=self.SEARCH_BAR)
        return LocationPickerScreen(self.driver, self.safety_policy, self.timeout)
