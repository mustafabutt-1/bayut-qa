"""Feature area: TruBroker™ & Find My Agent — Agent Transactions tab.

Ported from appium/tests/test_agent_last_transaction.py (docs/DECISIONS.md D-019).

The exact literal deal-card values below (amount, date, status="Pending") are kept
verbatim from the source suite on purpose, NOT because they're guaranteed stable —
its own comment documents this exact field drifting live (Pending -> Rejected) between
runs. Marked xfail rather than skipped: a failure here is real signal (the transaction
status genuinely changed), just not a locator/framework regression.
"""
from __future__ import annotations

import os

import pytest

AGENCY = os.environ.get("TEST_LEAD_AGENCY_NAME", "")
AGENT = os.environ.get("TEST_LEAD_AGENT_NAME", "")


@pytest.mark.xfail(
    reason="Deal status is live backend data, observed to drift between runs "
           "(Pending -> Rejected) — see module docstring.",
    strict=False,
)
def test_agent_last_transaction_deal_card(home_screen):
    assert AGENCY and AGENT, "TEST_LEAD_AGENCY_NAME / TEST_LEAD_AGENT_NAME must be set in .env"

    more = home_screen.open_more()
    hub = more.open_find_my_agent()
    hub.switch_to_agencies()
    hub.open_search()
    hub.search(AGENCY)
    agency = hub.open_first_agency_result()
    hub.assert_agency_name_visible(AGENCY)

    agency.switch_to_agents_tab()
    profile = agency.open_agent(AGENT)
    assert profile.is_displayed()

    # Transactions loads asynchronously on this screen — see AgentProfileScreen.tap_tab()
    profile.tap_tab("Transactions", timeout=30)
    profile.assert_transactions_tab_content()
    profile.scroll_to_first_deal_card()

    values = profile.first_deal_card_values()
    assert values["tv_deal_amount"] == "AED 1,050,000"
    assert values["tv_deal_tag"] == "SALE"
    assert values["tv_deal_status"] == "Pending"
    assert values["tv_deal_location"] == "Fairview Residency, Business Bay, Dubai"
    assert values["tv_beds"] == "1 Bed"
    assert values["tv_area"] == "841 sqft"
    assert values["tv_category"] == "Apartment"
    assert values["tv_broker_badge"] == "Seller Agent"
    assert values["tv_date"] == "Sale Date: 04 Aug 2026"
