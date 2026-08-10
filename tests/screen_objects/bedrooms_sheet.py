"""Bedrooms picker bottom sheet — OBSERVED 2026-08-10. Fingerprint `1dbe89861292`."""
from __future__ import annotations

from .base import BaseScreen


class BedroomsSheet(BaseScreen):
    OPTION = "com.bayut.bayutapp:id/beds_cb"   # Studio/1-7/8+ — disambiguate by text
    APPLY = "com.bayut.bayutapp:id/confirm_tv"
    SCRIM = "com.bayut.bayutapp:id/touch_outside"

    OPTIONS = ("Studio", "1", "2", "3", "4", "5", "6", "7", "8+")

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.APPLY)

    def apply(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.APPLY)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
