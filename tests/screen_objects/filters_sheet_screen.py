"""Full Filters sheet — OBSERVED 2026-08-10. Fingerprint `200fe0593bc8`.

Opened from the leading filter-icon quick-filter chip on Properties results.
"""
from __future__ import annotations

from .base import BaseScreen


class FiltersSheetScreen(BaseScreen):
    CANCEL = "com.bayut.bayutapp:id/cancel_ib_tb"
    PROPERTIES_SECTION = "com.bayut.bayutapp:id/rb_properties"
    NEW_PROJECTS_SECTION = "com.bayut.bayutapp:id/rb_new_projects"
    BUY_RADIO = "com.bayut.bayutapp:id/buy_rb"
    RENT_RADIO = "com.bayut.bayutapp:id/rent_rb"
    LOCATION_SEARCH = "com.bayut.bayutapp:id/add_loc_et"
    COMMUTE_TOGGLE = "com.bayut.bayutapp:id/commute_switch"
    RESIDENTIAL_TYPE = "com.bayut.bayutapp:id/rb_residential"
    COMMERCIAL_TYPE = "com.bayut.bayutapp:id/rb_commercial"
    TRUCHECK_ICON = "com.bayut.bayutapp:id/trucheck_icon"
    TRUCHECK_SWITCH = "com.bayut.bayutapp:id/trucheck_switch"
    BEDROOM_CHIP = "com.bayut.bayutapp:id/frequency_cb"   # shared id with bath row; disambiguate by text/position
    RESET = "com.bayut.bayutapp:id/tv_reset_filters"
    SHOW_RESULTS_CTA = "com.bayut.bayutapp:id/search_tv"  # "Show <n> properties"
    TITLE = "com.bayut.bayutapp:id/title_tv_tb"  # marker used when reached via Home search bar

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.SHOW_RESULTS_CTA) or \
            self.is_present(resource_id=self.TITLE, timeout=2)

    def show_results_label(self) -> str:
        el = self.wait_for(resource_id=self.SHOW_RESULTS_CTA)
        return el.text

    def tap_property_type(self, type_name: str):
        """e.g. "Villa" / "Apartment" — plain text tap, confirmed live."""
        self.safe_tap(text=type_name)

    def show_results(self):
        """id/search_tv — CTA text is dynamic ("Show 6,009 properties"), must be
        targeted by id, never by its own text (confirmed live)."""
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.SHOW_RESULTS_CTA)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)

    def close(self):
        from .properties_results_screen import PropertiesResultsScreen
        self.safe_tap(resource_id=self.CANCEL)
        return PropertiesResultsScreen(self.driver, self.safety_policy, self.timeout)
