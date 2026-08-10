"""§3 App override / data retention — docs/REGRESSION-CHECKLIST.md, logged-out half only.

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
"""
from __future__ import annotations

import os

import pytest


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

    # Read the price from favourite_nth_listing()'s own return value, not a separate
    # first_listing_price() call beforehand — confirmed live: production's result
    # order can shift between two separate page_source reads, which previously made
    # this test favourite one listing while cross-checking the price of another.
    price = properties_screen.favourite_nth_listing(0)
    assert price is not None, "could not read the listing's price to cross-check after relaunch"

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
    # test_favourites.py's warm-session case is fine with the default). Not a retention
    # bug — confirmed live the data was there, just slower to arrive.
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
