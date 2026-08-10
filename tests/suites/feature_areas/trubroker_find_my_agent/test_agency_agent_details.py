"""Feature area: TruBroker™ & Find My Agent — docs/REGRESSION-CHECKLIST.md.

Ported from appium/tests/test_agency_agent_details.py (docs/DECISIONS.md D-019).
AGENCY/AGENT below are read from .env (TEST_LEAD_AGENCY_NAME / TEST_LEAD_AGENT_NAME) —
same QA-sanctioned agency this session's consequential lead test uses, since this
suite already has real, current data for it. All read-only browsing; nothing here
submits a lead or otherwise mutates the account.
"""
from __future__ import annotations

import os

AGENCY = os.environ.get("TEST_LEAD_AGENCY_NAME", "")
AGENT = os.environ.get("TEST_LEAD_AGENT_NAME", "")


def test_agency_agent_details(home_screen):
    assert AGENCY and AGENT, "TEST_LEAD_AGENCY_NAME / TEST_LEAD_AGENT_NAME must be set in .env"

    more = home_screen.open_more()
    hub = more.open_find_my_agent()
    hub.switch_to_agencies()
    hub.open_search()
    hub.search(AGENCY)
    agency = hub.open_first_agency_result()
    hub.assert_agency_name_visible(AGENCY)
    assert hub.is_present(text="RERA", timeout=10)

    agency.switch_to_agents_tab()
    profile = agency.open_agent(AGENT)
    assert profile.is_displayed()

    profile.assert_about_tab_content()

    profile.tap_tab("Properties")
    profile.assert_properties_tab_content()

    # Transactions loads asynchronously on this screen — see AgentProfileScreen.tap_tab()
    profile.tap_tab("Transactions", timeout=30)
    profile.assert_transactions_tab_content()

    hub2 = profile.open_agency_link()
    hub2.assert_agency_name_visible(AGENCY)
