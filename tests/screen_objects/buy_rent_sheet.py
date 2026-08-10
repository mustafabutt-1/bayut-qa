"""Buy/Rent picker bottom sheet — OBSERVED 2026-08-10. Fingerprint `535207a2b37c`."""
from __future__ import annotations

from .base import BaseScreen


class BuyRentSheet(BaseScreen):
    BUY = "com.bayut.bayutapp:id/rb_first"
    RENT = "com.bayut.bayutapp:id/rb_second"
    SCRIM = "com.bayut.bayutapp:id/touch_outside"   # UNCERTAIN — unlabeled, do not tap; use .back() to dismiss

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.BUY)

    def dismiss(self):
        """The scrim (touch_outside) is UNCERTAIN, not ALLOW — use the device back
        gesture to close, same as tools/crawler.py does for this exact sheet shape."""
        from .properties_results_screen import PropertiesResultsScreen
        self.back()
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
