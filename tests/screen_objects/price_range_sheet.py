"""Price Range picker bottom sheet — OBSERVED 2026-08-10. Fingerprint `737ce49f1ddb`."""
from __future__ import annotations

from .base import BaseScreen


class PriceRangeSheet(BaseScreen):
    MIN_INPUT = "com.bayut.bayutapp:id/range_et_min"
    MAX_INPUT = "com.bayut.bayutapp:id/range_et_max"
    APPLY = "com.bayut.bayutapp:id/confirm_tv"
    SCRIM = "com.bayut.bayutapp:id/touch_outside"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.APPLY)

    def apply(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.APPLY)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
