"""Generic read-only info popup (e.g. TruCheck) — OBSERVED 2026-08-10.

Fingerprint `3fc6712baa94` for the TruCheck variant. Its only tappable element is the
scrim (touch_outside), which is UNCERTAIN — dismiss via the back gesture instead, same
pattern as the other bottom sheets whose scrim isn't individually labeled.
"""
from __future__ import annotations

from .base import BaseScreen


class InfoPopupScreen(BaseScreen):
    SCRIM = "com.bayut.bayutapp:id/touch_outside"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.SCRIM)

    def dismiss(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.back()
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
