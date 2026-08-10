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
        """Select a location, typing to find it when it is not already on screen.

        A plain tap-by-text only works for something already rendered — a Popular chip,
        or a sub-location that happens to be visible. The sanctioned test location
        ("Al Napoca") is neither: it has to be typed into the picker's search field
        before any result exists to tap. Falling straight to `safe_tap(text=...)`
        produced a bare "element not found" that read as a broken locator rather than
        "you never searched for it".

        Typing goes through `mobile: shell`, not `send_keys` — same reason as
        find_my_agent_hub_screen.search() (D-019/D-026): Appium's own text entry does
        not reliably trigger this app's search-as-you-type listeners.
        """
        if self.is_present(resource_id=self.POPULAR_LOCATION_CHIP, text=name, timeout=2):
            self.safe_tap_row_containing(self.POPULAR_LOCATION_CHIP, name)
            return

        self.safe_tap(resource_id=self.SEARCH_INPUT)
        self.driver.execute_script("mobile: shell", {
            "command": "input",
            "args": ["text", name.replace(" ", "%s")],
            "includeStderr": True,
            "timeout": 5000,
        })
        assert self.is_present(resource_id=self.POPULAR_LOCATION_CHIP, text=name,
                               timeout=15), (
            f"typed {name!r} into the location search but no suggestion row with that "
            f"exact title appeared within 15s. Either the location does not exist in "
            f"this environment, or the search-as-you-type listener did not fire (check "
            f"the Appium server was started with --allow-insecure=uiautomator2:adb_shell)."
        )
        # Deliberately NOT safe_tap(text=name): after typing, `et_input` also carries
        # this text and is itself clickable, so a plain text match taps the search box
        # instead of the suggestion. Match the labelled row via its clickable parent.
        self.safe_tap_row_containing(self.POPULAR_LOCATION_CHIP, name)

    def confirm(self):
        """Only "Done" (tv_done) is present here in practice, no keyboard-IME
        ambiguity (confirmed live). Lands on the Filters screen, not results yet."""
        from .filters_sheet_screen import FiltersSheetScreen
        self.safe_tap(resource_id=self.DONE)
        return FiltersSheetScreen(self.driver, self.safety_policy, self.timeout)
