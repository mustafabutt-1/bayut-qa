"""Listing detail (DPV) — OBSERVED 2026-08-10 (this session) + confirmed by the ported
suite (docs/DECISIONS.md D-019), fingerprint `ddcc1ea36441` at initial scroll position.

The highest-stakes screen in the whole system: a tap on the wrong element here sends a
real lead to a real Dubai agency. `expand_content_sheet` / the property-info and
regulatory-info checks below reach further down the page (the ported suite's
confirmed-live technique for it), extending past what this session's own scroll-unaware
crawl reached on its own.
"""
from __future__ import annotations

from .base import BaseScreen


class ListingDetailScreen(BaseScreen):
    BACK = "com.bayut.bayutapp:id/ib_back_button"
    SHARE = "com.bayut.bayutapp:id/ib_share_button"          # BLOCK-SHARE
    FAVOURITE = "com.bayut.bayutapp:id/ib_favourite_button"
    LEAD_EMAIL = "com.bayut.bayutapp:id/btn_email"            # BLOCK-LEAD-EMAIL
    LEAD_CALL = "com.bayut.bayutapp:id/btn_call"               # BLOCK-LEAD-CALL
    LEAD_WHATSAPP = "com.bayut.bayutapp:id/btn_whatsapp"        # BLOCK-LEAD-WHATSAPP
    PRICE = "com.bayut.bayutapp:id/tv_currency_price"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.BACK)

    def go_back(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.BACK)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)

    def assert_favourite_button_visible(self, timeout: int = 10):
        assert self.is_present(resource_id=self.FAVOURITE, timeout=timeout)

    def expand_content_sheet(self):
        """The photo gallery sits behind the draggable content sheet — a swipe from a
        photo pages through images instead of dragging the sheet up. Anchor the swipe
        to the price text, which is always part of the sheet's own peek content
        (confirmed live in the ported suite). Not a tap, so not gated the same way —
        it's a drag on a fixed screen coordinate, not an interaction with a
        classifiable element."""
        # Confirmed live this session: ending the swipe too close to the very top of
        # the screen (0.15) risked the OS reading it as a pull-down-from-top gesture
        # and opening the system notification shade instead of just dragging the
        # in-app sheet. 0.25 still drags the sheet fully open but stays clear of that
        # zone.
        price_el = self.wait_for(resource_id=self.PRICE, timeout=10)
        loc = price_el.location
        size = self.driver.get_window_size()
        start_pct = (loc["x"] / size["width"], loc["y"] / size["height"])
        end_pct = (start_pct[0], 0.25)
        self.swipe(start_pct, end_pct)

    def assert_property_information_visible(self, timeout: int = 10):
        assert self.is_present(text="Property Information", timeout=timeout)

    def assert_regulatory_information_soft(self):
        """DLD-data-dependent — not present on every listing, so this is a soft check
        only (matches the ported suite: try to scroll to it, swallow a miss)."""
        try:
            self.scroll_into_view_by_text("Regulatory Information", max_swipes=6)
        except Exception:
            pass

    def assert_recommended_properties_visible(self, max_swipes: int = 8):
        self.scroll_into_view_by_text("Recommended Properties", max_swipes=max_swipes)
