"""Rental Frequency picker bottom sheet — OBSERVED 2026-08-10. Fingerprint `ef88951d3cf3`."""
from __future__ import annotations

from .base import BaseScreen


class RentalFrequencySheet(BaseScreen):
    OPTION = "com.bayut.bayutapp:id/frequency_cb"   # Yearly/Monthly/Weekly/Daily/Any — disambiguate by text
    APPLY = "com.bayut.bayutapp:id/confirm_tv"
    SCRIM = "com.bayut.bayutapp:id/touch_outside"

    OPTIONS = ("Yearly", "Monthly", "Weekly", "Daily", "Any")

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.APPLY)

    def apply(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.APPLY)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
