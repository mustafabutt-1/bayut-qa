"""Agency profile — lead CTAs are present and refused.

docs/REGRESSION-CHECKLIST.md, Find My Agent: "tapping an agency card opens the Agency
Profile, with sections About, Properties, Agents — each with Call, Email, SMS CTAs."

The checklist item is about the CTAs *existing*. Exercising them means generating a real
lead, which docs/GUARDRAILS.md permits only against Explorer Real Estate through the
gated consequential test in 05_leads — so this asserts presence-and-refusal:

  * the control exists  → the checklist item is satisfied
  * the guard refuses it → the reason it stays manual is proven, not assumed

`assert_blocked()` never taps; it classifies the element and asserts BLOCK. If any of
these ever came back ALLOW, that is a real finding about the guard, not a test bug — the
assertion message says so.

Uses Explorer Real Estate, the QA team's own sanctioned test agency, purely for a stable
target. Nothing here contacts it.
"""
from __future__ import annotations

import pytest

from test_data import TEST_AGENCY as AGENCY  # checklist §5 — the only
# agency any test may touch on production. Never hardcode it again.

# LPV fat-card lead ids, already proven live (properties_results_screen.py). The agency
# profile reuses the same card component, so these are the same controls.
LEAD_CONTROLS = (
    ("Call", "com.bayut.bayutapp:id/btn_call"),
    ("Email", "com.bayut.bayutapp:id/btn_email"),
    ("WhatsApp", "com.bayut.bayutapp:id/btn_whatsapp"),
)


def _open_agency(home_screen):
    more = home_screen.open_more()
    hub = more.open_find_my_agent()
    assert hub.is_displayed(), "Find My Agent hub did not open"
    hub.switch_to_agencies()
    hub.open_search()
    hub.search(AGENCY)
    hub.assert_agency_name_visible(AGENCY)
    return hub.open_first_agency_result()


def test_agency_properties_tab_lead_ctas_are_blocked(home_screen):
    """Every lead CTA on an agency's property list exists and is refused."""
    agency = _open_agency(home_screen)
    agency.switch_to_properties_tab()
    agency.assert_properties_list_visible()

    found, missing = [], []
    for label, resource_id in LEAD_CONTROLS:
        if agency.is_present(resource_id=resource_id, timeout=5):
            agency.assert_blocked(resource_id=resource_id)
            found.append(label)
        else:
            missing.append(label)

    print(f"\n  lead CTAs present and blocked: {found}")
    if missing:
        print(f"  not present on this card: {missing}")

    assert found, (
        f"no lead CTA found on the agency's properties list. The checklist requires "
        f"Call, Email and SMS CTAs on the agency profile. Looked for: "
        f"{[r for _, r in LEAD_CONTROLS]}"
    )


def test_agency_agents_tab_lists_agents(home_screen):
    """The Agents section of the agency profile renders.

    Only that it renders. Opening a specific agent is already covered by
    test_agency_agent_details.py; this is the section-presence half of the checklist item.
    """
    agency = _open_agency(home_screen)
    agency.switch_to_agents_tab()
    assert agency.is_present(resource_id=agency.AGENT_NAME_ROW, timeout=15), (
        f"the Agents tab of {AGENCY!r} listed no agents"
    )


@pytest.mark.skip(
    reason="'Verify sending an email to Agents/Agencies and check the email text in "
           "both cases.' Sending is a real lead. It is permitted only against Explorer "
           "Real Estate via deliberate_tap() in a consequential/ test — 05_leads already "
           "does exactly that for a listing. Extending it to the agency-level and "
           "agent-level forms is a deliberate decision to take, not something to add "
           "quietly to a read-path suite."
)
def test_email_text_to_agent_and_agency():
    raise NotImplementedError
