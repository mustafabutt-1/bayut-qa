"""Agency detail — feature area, docs/REGRESSION-CHECKLIST.md (TruBroker & Find My Agent)."""
from __future__ import annotations

from .base import BaseScreen, SafetyRefusal, tappable


class AgencyDetailScreen(BaseScreen):
    AGENTS_TAB = "com.bayut.bayutapp:id/tv_agents_tab"
    PROPERTIES_TAB = "com.bayut.bayutapp:id/tv_properties_tab"
    PROPERTIES_LIST = "com.bayut.bayutapp:id/rv_properties"
    PRICE_LABEL = "com.bayut.bayutapp:id/price_tv"
    THUMBNAIL = "com.bayut.bayutapp:id/thumb_iv"
    CONTACTED_BADGE = "com.bayut.bayutapp:id/tv_viewed_contacted"

    def switch_to_agents_tab(self):
        self.safe_tap(resource_id=self.AGENTS_TAB)

    def switch_to_properties_tab(self):
        self.safe_tap(resource_id=self.PROPERTIES_TAB)

    def assert_properties_list_visible(self, timeout: int = 10):
        assert self.is_present(resource_id=self.PROPERTIES_LIST, timeout=timeout)

    def first_property_price(self) -> str:
        el = self.wait_for(resource_id=self.PRICE_LABEL)
        return el.text

    def open_nth_property(self, index: int = 0):
        """Still goes through the safety gate like every other tap in this suite —
        opening a listing thumbnail is itself harmless (read-only, reversible with
        back), but classifying it rather than raw-clicking keeps this the only tap
        path, no exceptions for "obviously fine" taps."""
        web_els = self.driver.find_elements(*self._by(resource_id=self.THUMBNAIL))
        assert web_els, f"no elements found for resource_id={self.THUMBNAIL!r}"
        candidates = [el for el in tappable(self.current_elements(), include_nested=True)
                      if el.resource_id == self.THUMBNAIL]
        assert len(candidates) > index, (
            f"expected at least {index + 1} {self.THUMBNAIL!r} element(s), found {len(candidates)}"
        )
        target = candidates[index]
        allowed, decision = self.safety_policy.may_tap(target)
        if decision.verdict != "ALLOW":
            raise SafetyRefusal(
                f"refusing to tap {target.label!r}: safety verdict {decision.verdict} "
                f"({decision.rule_id or 'no matching rule'})"
            )
        web_els[index].click()

    AGENT_NAME_ROW = "com.bayut.bayutapp:id/tv_agent_name"

    def open_agent(self, name: str, max_swipes: int = 10):
        """Classified by resource-id (tv_agent_name), not the name text itself — a
        person's name is arbitrary and unsafe to allowlist by text globally.

        Manual swipe + is_present(), not scroll_into_view_by_text()'s native
        UiAutomator2 `scrollIntoView` — CONFIRMED live 2026-08-10: with several agent
        rows on screen at once (SL Bergen, Alexandru Garbanzo, SectorLabs Testing
        Agent E2E, Adrian Buda, SL Claim...), `scrollIntoView(text(name))` opened the
        wrong agent's profile instead of the one actually requested. This is the same
        failure class D-024 already found and fixed for the sign-in test's "Log Out"
        check — scrollIntoView can settle on some other element without a clean
        not-found signal — but that fix was deliberately left scoped to just the
        sign-in flow at the time ("used elsewhere — e.g. opening an agent from a
        list — are unchanged"). This is that unfixed spot, now fixed the same way."""
        from .agent_profile_screen import AgentProfileScreen

        found = self.is_present(text=name, timeout=1)
        for _ in range(max_swipes):
            if found:
                break
            self.swipe_up()
            found = self.is_present(text=name, timeout=1)
        assert found, f"agent {name!r} not found after scrolling {max_swipes} times"

        target = self._match(resource_id=self.AGENT_NAME_ROW, accessibility_id=None,
                              text=name, include_nested=True)
        assert target is not None, f"found {name!r} on screen but could not classify it"
        allowed, decision = self.safety_policy.may_tap(target)
        if decision.verdict != "ALLOW":
            raise SafetyRefusal(
                f"refusing to tap {target.label!r}: safety verdict {decision.verdict} "
                f"({decision.rule_id or 'no matching rule'})"
            )
        web_el = self.wait_for(resource_id=self.AGENT_NAME_ROW, text=name, timeout=3)
        web_el.click()
        return AgentProfileScreen(self.driver, self.safety_policy, self.timeout)

    def assert_contacted_badge(self, expected_price_text: str, timeout: int = 10):
        assert self.is_present(text=expected_price_text, timeout=timeout)
        badge = self.wait_for(resource_id=self.CONTACTED_BADGE, timeout=timeout)
        assert badge.text == "Contacted", f"expected 'Contacted' badge, got {badge.text!r}"
