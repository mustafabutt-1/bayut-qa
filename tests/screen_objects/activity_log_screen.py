"""Activity Log — Viewed / Contacted tabs (feature-area section in
docs/REGRESSION-CHECKLIST.md). Nested full-screen activity, no bottom nav."""
from __future__ import annotations

from .base import BaseScreen


class ActivityLogScreen(BaseScreen):
    VIEWED_TAB = "com.bayut.bayutapp:id/viewed_rb"
    CONTACTED_TAB = "com.bayut.bayutapp:id/contacted_rb"
    BACK = "com.bayut.bayutapp:id/back_btn"

    def open_viewed_tab(self):
        self.safe_tap(resource_id=self.VIEWED_TAB)

    def open_contacted_tab(self):
        self.safe_tap(resource_id=self.CONTACTED_TAB)

    def assert_entry_visible(self, text: str, timeout: int = 10):
        assert self.is_present(text=text, timeout=timeout), (
            f"expected {text!r} to appear in the Activity Log"
        )

    def go_back(self):
        from .more_screen import MoreScreen
        self.safe_tap(resource_id=self.BACK)
        return MoreScreen(self.driver, self.safety_policy, self.timeout)
