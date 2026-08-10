"""Favourites screen — §20 docs/REGRESSION-CHECKLIST.md.

Nested full-screen activity, no bottom nav — same as ActivityLogScreen, reached only
via More."""
from __future__ import annotations

from .base import BaseScreen


class FavouritesScreen(BaseScreen):
    MARKER = "com.bayut.bayutapp:id/favourites_rb"
    FIRST_CARD = "com.bayut.bayutapp:id/favourite_cb"
    BACK = "com.bayut.bayutapp:id/iv_back"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.MARKER)

    def wait_for_first_card(self, timeout: int = 10):
        """The screen shows grey loading-skeleton placeholders before real content
        arrives — wait for a real card rather than asserting immediately."""
        return self.wait_for(resource_id=self.FIRST_CARD, timeout=timeout)

    def go_back(self):
        from .more_screen import MoreScreen
        self.safe_tap(resource_id=self.BACK)
        return MoreScreen(self.driver, self.safety_policy, self.timeout)
