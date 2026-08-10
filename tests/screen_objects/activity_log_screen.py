"""Activity Log — Viewed / Contacted tabs (feature-area section in
docs/REGRESSION-CHECKLIST.md). Nested full-screen activity, no bottom nav."""
from __future__ import annotations

from .base import BaseScreen


class ActivityLogScreen(BaseScreen):
    VIEWED_TAB = "com.bayut.bayutapp:id/viewed_rb"
    CONTACTED_TAB = "com.bayut.bayutapp:id/contacted_rb"
    BACK = "com.bayut.bayutapp:id/back_btn"

    # The Recent Searches tab's resource-id has never been observed here — the crawl's
    # page-source dumps are gitignored, and the live session only needed Viewed and
    # Contacted. Matched on text until a run reports the real id.
    # [UNVERIFIED — replace with the resource-id, likely `recent_searches_rb` by the
    #  naming pattern of its two siblings, but NOT confirmed, so not hardcoded.]
    RECENT_TAB_TEXT = "Recent Searches"

    # Card anatomy inside Viewed / Contacted, per the checklist. Reuses the ids already
    # proven on the LPV fat card, which is the same component.
    FAVOURITE_CHECKBOX = "com.bayut.bayutapp:id/favourite_cb"
    PRICE_TV = "com.bayut.bayutapp:id/price_tv"

    def open_viewed_tab(self):
        self.safe_tap(resource_id=self.VIEWED_TAB)

    def open_contacted_tab(self):
        self.safe_tap(resource_id=self.CONTACTED_TAB)

    def open_recent_searches_tab(self):
        self.safe_tap(text=self.RECENT_TAB_TEXT)

    def visible_tab_labels(self) -> list[str]:
        """Every tab label currently on the Activity Log header, in left-to-right order.

        Read from the screen rather than assumed, so a renamed or removed tab shows up
        as a real finding instead of a locator miss.
        """
        tabs = [e for e in self.current_elements()
                if e.bounds and (e.text or e.content_desc)
                and (e.klass.endswith("RadioButton") or e.resource_id.endswith("_rb"))]
        return [(e.text or e.content_desc).strip()
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
