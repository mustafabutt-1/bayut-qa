"""§20 Favourites — CONSEQUENTIAL, opt-in only.

Favouriting writes real, persisted data against the test account
(`PROD-BLOCK-FAVOURITE`, docs/GUARDRAILS.md) — §20's own default-suite coverage
(`../test_favourites.py`) only proves the control exists and is refused. This file is
the other half: actually favouriting a listing and confirming it appears on the
Favourites screen, using `deliberate_tap_at()` — a real coordinate touch, not
`.click()`, since `.click()` is confirmed (D-031) to have no effect on this control at
all, and `.click()`-based `deliberate_tap()` can't be reused here for that reason.

Idempotency can't be read from the checkbox's own attributes — `checked`/`selected`
never change regardless of real state (D-031). Detected instead from a real
behavioural signal: tapping an ALREADY-favourited listing triggers a "Remove property
from Favourites?" confirmation (only on removal, never on addition). If that dialog
appears, this test declines it (`btn_no`, ALLOW-BAYUT-CONFIRM-DIALOG-DECLINE — declining
is always safe, it's the dialog's own refusal branch) and retries once against the next
listing, rather than silently removing an earlier run's favourite.

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


def _favourite_first_listing(properties_screen, home_screen, max_attempts: int = 2) -> str:
    """Tap the first listing's heart and prove it landed, retrying once if the tap
    instead removed an already-favourited listing (see module docstring)."""
    driver = home_screen.driver
    for attempt in range(1, max_attempts + 1):
        price, center = properties_screen.locate_favourite_checkbox(0)
        assert price is not None, "could not read the first listing's price"

        deliberate_tap_at(
            driver, *center,
            reason=f"§20 Favourites: favourite the first listing ({price!r}) to prove "
                   f"it appears on the Favourites screen",
            evidence_tag="favourites-add",
        )

        if properties_screen.is_present(text="Remove property from Favourites?", timeout=2):
            properties_screen.safe_tap(resource_id="com.bayut.bayutapp:id/btn_no")
            assert attempt < max_attempts, (
                f"favourited the first listing ({price!r}) twice and it still shows "
                f"the removal-confirmation dialog — the heart is toggling but nothing "
                f"useful is happening; that's a real finding, not a test-setup problem"
            )
            properties_screen = home_screen.open_properties()
            continue

        return price
    raise AssertionError("unreachable")


def test_favourite_listing_appears_in_favourites(properties_screen, home_screen):
    price = _favourite_first_listing(properties_screen, home_screen)

    more = home_screen.open_more()
    favourites = more.open_favourites()
    assert favourites.is_displayed()
    favourites.wait_for_first_card()
    assert favourites.is_present(text=price, timeout=10), (
        f"favourited listing (price {price!r}) did not appear on the Favourites screen"
    )
