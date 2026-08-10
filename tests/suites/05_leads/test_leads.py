"""§5 Leads (Email, Phone, SMS, WhatsApp) — docs/REGRESSION-CHECKLIST.md.

Scope of what's automated here, and why it stops where it stops:

The checklist item is "verify leads work correctly" from 16 different entry points
(LPV, DPV, Gallery View, Agent/Agency LPV/DPV, Area Prime Slot, ...). Actually
completing a lead is explicitly, permanently manual-only — CLAUDE.md: "Tapping a
contact-agent control sends a real lead to a real Dubai agency." No amount of
tooling maturity changes that; it needs a staging environment with a disposable test
agency (PROJECT-STATE.md open decision #1) before "the lead actually arrives" can ever
be asserted by a machine.

What automation *can* verify, safely, forever: that the lead controls are present where
the checklist says they should be, and that they are structurally recognised as
consequential by the tap gate every single build. A control that quietly stops being
BLOCK is exactly the kind of regression a human skimming the screen would never notice.

Entry points covered: LPV, DPV. The other 14 are not yet reached by any crawl.
"""
from __future__ import annotations

from screen_objects.base import SafetyRefusal


def test_lead_controls_blocked_on_lpv(properties_screen):
    """LPV: Email/Call/WhatsApp on the first listing fat card are present and BLOCK."""
    properties_screen.assert_blocked(resource_id=properties_screen.LEAD_EMAIL)
    properties_screen.assert_blocked(resource_id=properties_screen.LEAD_CALL)
    properties_screen.assert_blocked(resource_id=properties_screen.LEAD_WHATSAPP)


def test_lead_controls_blocked_on_dpv(properties_screen):
    """DPV: Email/Call/WhatsApp are present and BLOCK on the listing detail page."""
    dpv = properties_screen.open_first_listing()
    try:
        assert dpv.is_displayed()
        dpv.assert_blocked(resource_id=dpv.LEAD_EMAIL)
        dpv.assert_blocked(resource_id=dpv.LEAD_CALL)
        dpv.assert_blocked(resource_id=dpv.LEAD_WHATSAPP)
    finally:
        dpv.go_back()


def test_lead_controls_cannot_be_tapped_via_safe_tap(properties_screen):
    """Defence in depth: even a direct safe_tap() attempt on a lead control must raise,
    not silently no-op. Proves the refusal is load-bearing, not just an assertion helper
    that happens to agree with itself."""
    import pytest

    with pytest.raises(SafetyRefusal):
        properties_screen.safe_tap(resource_id=properties_screen.LEAD_CALL)
