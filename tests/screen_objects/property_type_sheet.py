"""Property Types picker bottom sheet — OBSERVED 2026-08-10. Fingerprint `68d2854fde8c`."""
from __future__ import annotations

from .base import BaseScreen


class PropertyTypeSheet(BaseScreen):
    RESIDENTIAL = "com.bayut.bayutapp:id/rb_residential"
    COMMERCIAL = "com.bayut.bayutapp:id/rb_commercial"
    APPLY = "com.bayut.bayutapp:id/tv_apply"
    SCRIM = "com.bayut.bayutapp:id/touch_outside"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.APPLY)

    def apply(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.APPLY)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
