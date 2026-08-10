"""Agent profile — About / Properties / Transactions tabs.

feature area, docs/REGRESSION-CHECKLIST.md (TruBroker & Find My Agent).
"""
from __future__ import annotations

from .base import BaseScreen


class AgentProfileScreen(BaseScreen):
    NAME = "com.bayut.bayutapp:id/tv_agent_name"
    TAB_CONTAINER = "com.bayut.bayutapp:id/tab_layout"
    SELECT_LOCATION_PROPERTIES = "com.bayut.bayutapp:id/tv_select_location_properties"
    PROPERTY_PURPOSE_GROUP = "com.bayut.bayutapp:id/rg_property_purpose"
    DEAL_SUMMARY_HEADING = "com.bayut.bayutapp:id/tv_deal_summary"
    DEAL_CLOSED_HEADING = "com.bayut.bayutapp:id/tv_deal_closed"
    AGENCY_LINK = "com.bayut.bayutapp:id/cl_agency_detail"
    BACK = "com.bayut.bayutapp:id/iv_back_button"

    DEAL_FIELDS = (
        "tv_deal_amount", "tv_deal_tag", "tv_deal_status", "tv_deal_location",
        "tv_beds", "tv_area", "tv_category", "tv_broker_badge", "tv_date",
    )

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.NAME, timeout=10)

    def tap_tab(self, tab_text: str, timeout: int | None = None):
        """Plain tap-by-text is ambiguous three ways on this screen (a stale prior-
        screen tab, an in-page subheading, and the real tab) — anchor via xpath scoped
        to the uniquely-id'd tab container, same fix the ported suite arrived at.

        Classification target is the exact xpath-located element (matched by bounds
        against a fresh page_source parse), not a separate unscoped `_match(text=...)`
        search. CONFIRMED live 2026-08-10: an unscoped text search for "Properties"
        found a *different*, unrelated element elsewhere on screen sharing the same
        label — Agency Detail's own `tv_properties_tab` toggle, which already has its
        own ALLOW rule — and classified against that one instead of the tab actually
        being tapped. That happened to still be ALLOW, so it went unnoticed; a search
        for "Transactions" had no such coincidental match and correctly surfaced as
        UNCERTAIN, exposing the bug. These tab labels have no resource-id of their
        own (see the new ALLOW-BAYUT-AGENT-PROFILE-TABS rule for why bare text needed
        its own allowlisting here), so bounds is the only reliable way to say "this
        exact element, not some other one that happens to share its text".

        `timeout` defaults to the screen's own (15s) but Transactions specifically may
        need longer — CONFIRMED live 2026-08-10: About/Properties are present from
        first render, but Transactions is added to this tab bar asynchronously (a
        separate, slower backend call for the agent's deal history), sometimes after
        15s have already elapsed. Polled directly: absent at first, present moments
        later on the identical unchanged screen — a real load-timing race, not a
        locator bug or a conditionally-missing tab."""
        import logging

        from appium.webdriver.common.appiumby import AppiumBy
        from selenium.webdriver.support.ui import WebDriverWait

        xpath = f'//*[@resource-id="{self.TAB_CONTAINER}"]//*[@text="{tab_text}"]'
        logging.warning(
            "XPath locator in use (last-resort per CLAUDE.md's locator priority): "
            "%s — breaks if the tab container's structure changes, unlike a stable "
            "resource-id/accessibility-id.", xpath,
        )
        web_el = WebDriverWait(self.driver, timeout or self.timeout).until(
            lambda d: d.find_element(AppiumBy.XPATH, xpath)
        )
        rect = web_el.rect
        target_bounds = (rect["x"], rect["y"], rect["x"] + rect["width"], rect["y"] + rect["height"])
        target = next((el for el in self.current_elements() if el.bounds == target_bounds), None)
        assert target is not None, (
            f"tab {tab_text!r} located via xpath at {target_bounds} but no matching "
            f"element found in a fresh page_source parse for safety classification"
        )
        allowed, decision = self.safety_policy.may_tap(target)
        if decision.verdict != "ALLOW":
            from .base import SafetyRefusal
            raise SafetyRefusal(
                f"refusing to tap tab {tab_text!r}: safety verdict {decision.verdict} "
                f"({decision.rule_id or 'no matching rule'})"
            )
        web_el.click()

    def assert_about_tab_content(self):
        assert self.is_present(text="Expertise", timeout=10)
        assert self.is_present(text="Service Areas", timeout=5)

    def assert_properties_tab_content(self):
        assert self.is_present(resource_id=self.SELECT_LOCATION_PROPERTIES, timeout=10)
        assert self.is_present(resource_id=self.PROPERTY_PURPOSE_GROUP, timeout=5)

    def assert_transactions_tab_content(self):
        assert self.is_present(resource_id=self.DEAL_SUMMARY_HEADING, timeout=10)
        assert self.is_present(resource_id=self.DEAL_CLOSED_HEADING, timeout=5)

    def scroll_to_first_deal_card(self):
        self.scroll_into_view_by_id(self.DEAL_CLOSED_HEADING, max_swipes=8)

    def first_deal_card_values(self) -> dict[str, str | None]:
        values = {}
        for field in self.DEAL_FIELDS:
            els = self.driver.find_elements(*self._by(resource_id=f"com.bayut.bayutapp:id/{field}"))
            values[field] = els[0].text if els else None
        return values

    def open_agency_link(self):
        from .find_my_agent_hub_screen import FindMyAgentHubScreen
        self.safe_tap(resource_id=self.AGENCY_LINK)
        return FindMyAgentHubScreen(self.driver, self.safety_policy, self.timeout)

    def go_back(self):
        self.safe_tap(resource_id=self.BACK)
