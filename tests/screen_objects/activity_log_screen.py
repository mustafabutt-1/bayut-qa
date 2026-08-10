"""Activity Log — Viewed / Contacted tabs (feature-area section in
docs/REGRESSION-CHECKLIST.md). Nested full-screen activity, no bottom nav."""
from __future__ import annotations

from .base import BaseScreen


class ActivityLogScreen(BaseScreen):
    VIEWED_TAB = "com.bayut.bayutapp:id/viewed_rb"
    CONTACTED_TAB = "com.bayut.bayutapp:id/contacted_rb"
    BACK = "com.bayut.bayutapp:id/back_btn"

    # OBSERVED 2026-08-10, build 15.7.2 (1272): the three tabs are a RadioGroup
    # (rg_activity_log) of searches_rb / viewed_rb / contacted_rb. Note the id is
    # `searches_rb`, NOT the `recent_searches_rb` the sibling naming pattern suggested —
    # which is exactly why it was left as a text match until a real run reported it.
    RECENT_TAB = "com.bayut.bayutapp:id/searches_rb"
    TAB_GROUP = "com.bayut.bayutapp:id/rg_activity_log"
    TITLE = "com.bayut.bayutapp:id/tv_activity"           # "Your Activity"
    RECENT_SEARCHES_LIST = "com.bayut.bayutapp:id/rv_recent_searches"

    # Card anatomy inside Viewed / Contacted, per the checklist. Reuses the ids already
    # proven on the LPV fat card, which is the same component.
    FAVOURITE_CHECKBOX = "com.bayut.bayutapp:id/favourite_cb"
    PRICE_TV = "com.bayut.bayutapp:id/price_tv"

    def open_viewed_tab(self):
        self.safe_tap(resource_id=self.VIEWED_TAB)

    def open_contacted_tab(self):
        self.safe_tap(resource_id=self.CONTACTED_TAB)

    def is_displayed(self, timeout: int = 10) -> bool:
        return self.is_present(resource_id=self.TAB_GROUP, timeout=timeout)

    def open_recent_searches_tab(self):
        self.safe_tap(resource_id=self.RECENT_TAB)

    #: The three documented tabs, by resource-id. Identity is the id; the label is only
    #: ever read as a value for reporting, never used to find the element.
    TAB_IDS: dict[str, str] = {
        "Recent Searches": RECENT_TAB,
        "Viewed": VIEWED_TAB,
        "Contacted": CONTACTED_TAB,
    }

    def present_tab_ids(self) -> dict[str, bool]:
        """Which documented tabs exist, keyed by name, resolved purely by resource-id."""
        present = {e.resource_id for e in self.current_elements() if e.resource_id}
        return {name: rid in present for name, rid in self.TAB_IDS.items()}

    def visible_tab_labels(self) -> list[str]:
        """The tabs' visible labels, left to right — for reporting only.

        Elements are located by resource-id; the text is read afterwards as a value. A
        localized build returns different strings here and that is fine, because nothing
        asserts on them — `present_tab_ids()` is what the tests check.
        """
        tabs = [e for e in self.current_elements()
                if e.resource_id in self.TAB_IDS.values() and e.bounds]
        return [(e.text or e.content_desc or e.resource_id.rsplit("/", 1)[-1]).strip()
                for e in sorted(tabs, key=lambda e: e.bounds[0])]

    def card_count(self) -> int:
        return sum(1 for e in self.current_elements()
                   if e.resource_id == self.PRICE_TV)

    def assert_entry_visible(self, text: str, timeout: int = 10):
        assert self.is_present(text=text, timeout=timeout), (
            f"expected {text!r} to appear in the Activity Log"
        )

    def go_back(self):
        from .more_screen import MoreScreen
        self.safe_tap(resource_id=self.BACK)
        return MoreScreen(self.driver, self.safety_policy, self.timeout)
