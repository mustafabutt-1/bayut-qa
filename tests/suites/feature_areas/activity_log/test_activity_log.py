"""Activity Log — docs/REGRESSION-CHECKLIST.md, "Activity Log" feature area.

Four checklist items:
  1. Recent Searches / Viewed / Contacted all display on "Your Activity"
  2. Stored filters are re-applied when a recent search is opened
  3. A past-days search moves to the top when tapped, staying in the past-days section
  4. Fat cards in Viewed/Contacted show badges, image change, favourite heart

Item 1 and the read-path half of 4 are covered here. Items 2 and 3 need pre-existing
history that a fresh device does not have, so they skip with an explicit reason rather
than silently passing on an empty list — an empty Activity Log proves nothing, and a
green test that proved nothing is worse than a skip.

The favourite heart is asserted **present, not tapped**: on production a write to
favourites is guarded (docs/GUARDRAILS.md). §20 covers the tap itself.
"""
from __future__ import annotations

import pytest


def _open_activity_log(home_screen):
    more = home_screen.open_more()
    assert more.is_displayed(), "More screen did not open"
    return more.open_activity_log()


def test_all_three_activity_tabs_present(home_screen):
    """Checklist item 1 — the three tabs exist on Your Activity."""
    activity = _open_activity_log(home_screen)
    labels = activity.visible_tab_labels()
    print(f"\n  tabs observed: {labels}")

    normalised = {"".join(l.lower().split()) for l in labels}
    expected = ("Recent Searches", "Viewed", "Contacted")
    missing = [e for e in expected if "".join(e.lower().split()) not in normalised]

    assert not missing, (
        f"Activity Log is missing tab(s): {missing}. Observed: {labels}. "
        f"If a tab was merely renamed, fix ActivityLogScreen — that is a TEST DEFECT, "
        f"not an app defect."
    )


def test_viewed_tab_cards_expose_favourite_heart(home_screen):
    """Checklist item 4, read-path half — card anatomy in Viewed.

    Skips on an empty Viewed list. Open a listing first (§18 does exactly this and
    already asserts it lands here) if you want this to run on a fresh device.
    """
    activity = _open_activity_log(home_screen)
    activity.open_viewed_tab()

    count = activity.card_count()
    print(f"\n  Viewed cards: {count}")
    if count == 0:
        pytest.skip(
            "Viewed tab is empty on this device — nothing to inspect. Run "
            "18_detail_page_dpv first, which opens a listing and populates Viewed."
        )

    assert activity.is_present(resource_id=activity.FAVOURITE_CHECKBOX), (
        "no favourite heart on any Viewed card — the checklist requires fat cards in "
        "Viewed/Contacted to carry it"
    )


def test_contacted_tab_opens(home_screen):
    """Checklist item 1 — the Contacted tab is reachable and renders.

    Deliberately does not assert the tab is non-empty. Populating Contacted means
    generating a real lead, which is permitted only against Explorer Real Estate through
    the gated consequential test (05_leads) — not a precondition for this one.
    """
    activity = _open_activity_log(home_screen)
    activity.open_contacted_tab()
    count = activity.card_count()
    print(f"\n  Contacted cards: {count}")
    assert activity.is_present(resource_id=activity.CONTACTED_TAB), (
        "Contacted tab did not stay selected after tapping it"
    )


@pytest.mark.skip(
    reason="Checklist items 2 and 3 (stored filters re-applied on opening a recent "
           "search; past-days search moves to top). Both need pre-existing multi-day "
           "search history, which no fresh run has. Needs a decision on how to seed it: "
           "either a device kept warm across runs, or accept these two as manual."
)
def test_recent_search_reapplies_stored_filters(home_screen):
    raise NotImplementedError
