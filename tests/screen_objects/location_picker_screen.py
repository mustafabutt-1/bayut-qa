"""Location picker — OBSERVED 2026-08-10. Fingerprint `fd1b1ab04856`.

No element on this screen carries a content-desc (full fingerprint == structural
fingerprint) — every locator here is resource-id, per docs/REGRESSION-CHECKLIST.md
locator-quality note. The 17 location-level restriction rules in the checklist (§13)
are NOT verified here — that needs PROBE mode against `context/filter-inventory.md`,
not a structural crawl.
"""
from __future__ import annotations

from .base import BaseScreen


class LocationPickerScreen(BaseScreen):
    CLOSE = "com.bayut.bayutapp:id/iv_close"
    SEARCH_INPUT = "com.bayut.bayutapp:id/et_input"
    POPULAR_LOCATION_CHIP = "com.bayut.bayutapp:id/tv_title"   # Dubai/Sharjah/Ajman/etc, disambiguate by text
    RESET = "com.bayut.bayutapp:id/tv_reset"
    DONE = "com.bayut.bayutapp:id/tv_done"

    POPULAR_LOCATIONS = (
        "Dubai", "Sharjah", "Ajman", "Abu Dhabi",
        "Ras Al Khaimah", "Umm Al Quwain", "Fujairah", "Al Ain",
    )

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.SEARCH_INPUT)

    def close(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.CLOSE)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)

    def select_location(self, name: str):
        """Confirmed live (ported suite) for both an exact Popular-Locations chip
        (e.g. "Dubai") and a sub-location not in that list (e.g. "Business Bay") —
        both resolve to a plain tap-by-text once the picker is open."""
        self.safe_tap(text=name)

    def confirm(self):
        """Only "Done" (tv_done) is present here in practice, no keyboard-IME
        ambiguity (confirmed live). Lands on the Filters screen, not results yet."""
        from .filters_sheet_screen import FiltersSheetScreen
        self.safe_tap(resource_id=self.DONE)
        return FiltersSheetScreen(self.driver, self.safety_policy, self.timeout)
