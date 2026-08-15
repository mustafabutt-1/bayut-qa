"""§3 App override / data retention — docs/REGRESSION-CHECKLIST.md, logged-out half only.

CONSEQUENTIAL, opt-in only — moved here from the default suite because proving
"favourites survive a relaunch" requires first creating a real favourite
(`PROD-BLOCK-FAVOURITE`, docs/GUARDRAILS.md), the same reasoning
`20_favourites/consequential/test_favourites.py` already documents. Uses
`deliberate_tap_at()`, not `.click()` — confirmed (D-031) `.click()` has no effect on
this control at all.

**What this actually tests, and what it doesn't.** The checklist means installing a new
APK *build* over the existing one and checking local data survives the upgrade. This
suite has no second build to install — there is only ever one Bayut build on the test
device — so a real override can't be reproduced. What's tested instead is the weaker,
necessary-but-not-sufficient precondition: does the same data survive an ordinary
process kill + relaunch (`terminate_app` + `activate_app`, never `pm clear` — see
docs/DECISIONS.md D-015)? A build that fails this would certainly fail a real override
too, but passing this is not proof an override would also pass (a migration bug on
first-run-after-upgrade wouldn't show up here at all). Revisit with a real second build
if one ever becomes available for this device.

**Coverage gap, stated plainly.** The checklist's logged-out list is Favourites; Recent
Searches / Last Search; BayutGPT queries and responses; Activity Log (Recent Searches,
Viewed, Contacted). Only Favourites and Activity Log's Viewed tab are covered here —
Recent Searches/Last Search has no located Home-screen element yet (see
`screen_objects/home_screen.py`'s own docstring), and BayutGPT has no screen object at
all yet. Both are UNKNOWN, not silently assumed passing.

The logged-in half of this checklist item (user stays logged in, Saved Searches,
Alerts) is intentionally not in this file — it additionally exercises the sign-in
consequential flow and belongs with that, not bundled into a plain data-retention check.

Requires RUN_CONSEQUENTIAL_TESTS=1 to run at all — a real environment check, not just a
folder/marker convention, so `pytest tests/` alone can never trigger this.
"""
from __future__ import annotations

import os

import pytest

from screen_objects.consequential import deliberate_tap_at

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CONSEQUENTIAL_TESTS") != "1",
    reason="Consequential test (favourites a real listing against the test account). "
           "Set RUN_CONSEQUENTIAL_TESTS=1 to run deliberately.",
)


def _ensure_first_listing_favourited(properties_screen, home_screen) -> str:
    """Favourite the first listing and PROVE it, retrying once if the tap toggled it off.

    The heart is a toggle, not an "ensure", and its state cannot be read from the card:

      * `favourite_cb.checked` stays False whether or not the listing is favourited
        (D-031, re-confirmed 2026-08-11), so there is nothing on the card to inspect.
      * Tapping an already-favourited listing shows a "Remove property from
        Favourites?" confirmation instead — decline it (`btn_no`) and retry against
        the next listing, rather than silently removing an earlier run's favourite.

    So a single tap on a listing left favourited by an earlier run REMOVES it, and the
    persistence assertion then fails for a reason that has nothing to do with
    persistence — which is exactly the false defect this checklist item must not
    produce. Favourites accumulate across runs, so this is the normal case, not an edge
    one.

    Verifying here also sharpens the test: it now separately establishes "the favourite
    was recorded" and "it survived the relaunch", instead of conflating the two.
    """
    driver = home_screen.driver
    for attempt in (1, 2):
        price, center = properties_screen.locate_favourite_checkbox(0)
        assert price is not None, "could not read the listing's price to cross-check"

        deliberate_tap_at(
            driver, *center,
            reason=f"§3 App override: favourite the first listing ({price!r}) to prove "
                   f"it survives a kill+relaunch",
            evidence_tag="app-override-favourite",
        )

        if properties_screen.is_present(text="Remove property from Favourites?", timeout=2):
            properties_screen.safe_tap(resource_id="com.bayut.bayutapp:id/btn_no")
            assert attempt == 1, (
                f"favourited the first listing ({price!r}) twice and it still shows "
                f"the removal-confirmation dialog — the heart is toggling but nothing "
                f"useful is happening; that's a real finding, not a test-setup problem"
            )
            properties_screen = home_screen.open_properties()
            continue

        favourites = home_screen.open_more().open_favourites()
        favourites.wait_for_first_card(timeout=20)
        recorded = favourites.is_present(text=price, timeout=10)

        # Favourites is a nested full-screen activity with NO bottom nav, so nothing
        # here may call open_more()/open_properties() directly — go back to More the
        # way the screen object does, exactly as the assertions further down do.
        more_again = favourites.go_back()
        if recorded:
            return price

        assert attempt == 1, (
            f"favourited the first listing ({price!r}) twice and it is still not on the "
            f"Favourites screen. The heart is toggling but nothing is being recorded — "
            f"that is a real finding, not a test-setup problem."
        )
        assert more_again.is_displayed(), "expected to be back on More after Favourites"
        properties_screen = home_screen.open_properties()
    raise AssertionError("unreachable")


def test_favourites_and_viewed_activity_persist_across_relaunch(properties_screen, home_screen):
    more = home_screen.open_more()
    if more.is_signed_in():
        pytest.skip(
            "this checklist item is specifically for a logged-out user; the device is "
            "currently signed in — run this after signing out, or see "
            "tests/suites/04_sign_in_up/consequential/test_sign_in.py"
        )

    # open_more() navigated away from Properties — the `properties_screen` fixture
    # object still refers to that screen conceptually, but page_source now reflects
    # wherever the app actually is. Re-navigate before reading anything from it.
    properties_screen = home_screen.open_properties()

    price = _ensure_first_listing_favourited(properties_screen, home_screen)
    properties_screen = home_screen.open_properties()

    dpv = properties_screen.open_first_listing()
    assert dpv.is_displayed()
    dpv.go_back()

    driver = home_screen.driver
    driver.terminate_app(os.environ["BAYUT_APP_PACKAGE"])
    driver.activate_app(os.environ["BAYUT_APP_PACKAGE"])

    assert home_screen.is_displayed(timeout=10), (
        "expected to land back on Home after relaunch, same as a plain app resume "
        "(onboarding is one-time and data-gated, not process-gated — D-015)"
    )

    more_after = home_screen.open_more()
    assert not more_after.is_signed_in(), (
        "expected to still be logged out after relaunch — a sign-in state change here "
        "would itself be a retention bug, just not the one this test is checking"
    )

    favourites = more_after.open_favourites()
    # Longer than wait_for_first_card()'s normal 10s default — OBSERVED 2026-08-10:
    # right after a cold terminate_app+activate_app, this screen's network fetch takes
    # noticeably longer than a plain in-session navigation to it (20_favourites/
    # consequential/test_favourites.py's warm-session case is fine with the default).
    # Not a retention bug — confirmed live the data was there, just slower to arrive.
    favourites.wait_for_first_card(timeout=25)
    assert favourites.is_present(text=price, timeout=10), (
        f"expected the favourited listing (price {price!r}) to still be present on "
        f"the Favourites screen after a kill+relaunch"
    )

    # Favourites is a nested full-screen activity with no bottom nav (same as
    # ActivityLogScreen) — home_screen.open_more() would look for a "More" nav item
    # that isn't there. Go back to More the same way ActivityLogScreen.go_back() does.
    more_again = favourites.go_back()
    activity_log = more_again.open_activity_log()
    activity_log.open_viewed_tab()
    activity_log.assert_entry_visible(price, timeout=20)
