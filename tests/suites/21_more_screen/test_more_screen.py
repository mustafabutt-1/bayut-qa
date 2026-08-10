"""§21 More screen — docs/REGRESSION-CHECKLIST.md.

The checklist gives two section lists, one per auth state. Rather than hardcoding an
assumption about which state the device is in, these read the state from the screen
(`is_signed_in()`, D-027's scroll-free signal) and assert the matching list.

Advisory sections (dated promos, agent-only rows) are reported, not failed — a 2024
awards banner may legitimately have been retired, and role-scoped rows depend on the
signed-in account type. Failing on those would train the team to ignore this test.
"""
from __future__ import annotations


def test_more_screen_sections_present_for_current_auth_state(home_screen):
    more = home_screen.open_more()
    assert more.is_displayed(), "More screen did not open"

    signed_in = more.is_signed_in()
    expected = more.SECTIONS_SIGNED_IN if signed_in else more.SECTIONS_UNSIGNED
    labels = more.visible_section_labels()

    print(f"\n  auth state : {'SIGNED IN' if signed_in else 'SIGNED OUT'}")
    print(f"  labels seen: {len(labels)}")

    missing = more.missing_sections(expected, labels)
    advisory_missing = more.missing_sections(more.SECTIONS_ADVISORY, labels)
    if advisory_missing:
        print(f"  advisory (reported, not failed): {advisory_missing}")

    assert not missing, (
        f"More screen is missing {len(missing)} section(s) the checklist requires for a "
        f"{'signed-in' if signed_in else 'signed-out'} user:\n"
        f"  missing : {missing}\n"
        f"  seen    : {labels}\n"
        f"If a label was merely reworded, correct MoreScreen.SECTIONS_* rather than "
        f"filing a defect — that would be a TEST DEFECT, not an app defect."
    )


def test_sign_out_is_blocked_outside_a_consequential_test(home_screen):
    """Log Out must be refused by the normal gate.

    §21 lists Log Out for signed-in users and it is genuinely part of regression, but it
    destroys the session mid-run, so BLOCK-LOGOUT refuses it here. The sanctioned path is
    a `consequential/` test using `deliberate_tap()` (D-019). Skips when signed out,
    where the control does not exist.
    """
    import pytest

    more = home_screen.open_more()
    if not more.is_signed_in():
        pytest.skip("signed out — no Log Out control on screen")
    more.scroll_into_view_by_text("Log Out")
    more.assert_blocked(text="Log Out")


def test_manage_alerts_entry_is_present(home_screen):
    """Manage Alerts is reachable from More.

    Only presence is checked. Creating or toggling an alert is PROD-BLOCK-SAVE-SEARCH /
    BLOCK-NOTIFICATION-OPTIN — real recurring email and push to a real inbox — so the
    Alerts feature area stays manual on production (docs/GUARDRAILS.md).
    """
    more = home_screen.open_more()
    more.scroll_into_view_by_text("Manage Alerts")
    assert more.is_present(text="Manage Alerts"), (
        "'Manage Alerts' row not found on the More screen"
    )
