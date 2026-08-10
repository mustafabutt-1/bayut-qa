"""TruBroker LPV widget — location visibility rules.

docs/REGRESSION-CHECKLIST.md, "TruBroker™ & Find My Agent":

  * not shown at Emirates / UAE level
  * shown for Loc 3 and further, in Dubai and Abu Dhabi only
  * visible to agents and end users, logged in or out
  * **not** shown when multiple locations are entered

Which of these are hard assertions and which are not is the whole design of this file.

The two *negative* rules are unconditional: at emirate level, and with multiple
locations, the widget must be absent. Nothing about data availability can make it
legitimately appear, so those fail loudly.

The *positive* rule cannot be asserted the same way. §16 states only inline widgets
containing data are visible, and the TruBroker widget renders the top TruBrokers for
that location — so a Loc 3 area with no TruBrokers legitimately shows nothing. Asserting
presence there would fail on a data condition, not a defect, and a test that cries wolf
on live inventory gets ignored within two sprints. It reports and skips instead.

These are slow: each one re-applies locations and scrolls the result set.
"""
from __future__ import annotations

import pytest

WIDGET = "TruBroker"

# Loc 1. The checklist names all eight emirates in the Popular section (§13).
EMIRATE = "Dubai"
# Loc 3 under Dubai. The checklist's own examples for third-level-or-above locations
# (§14, Area Prime Slot) are Business Bay, Downtown Dubai and JVC.
LOC3_DUBAI = "Business Bay"
SECOND_LOCATION = "Dubai Marina"


def test_widget_not_shown_at_emirate_level(properties_screen):
    """Hard rule: no TruBroker widget at Loc 1."""
    results = properties_screen.search_locations(EMIRATE)
    observed = results.observed_widget_order()
    print(f"\n  location: {EMIRATE} (emirate / Loc 1)")
    print(f"  widgets seen: {[n for n, _ in observed]}")

    assert WIDGET not in dict(observed), (
        f"TruBroker widget appeared at emirate level ({EMIRATE}). The checklist states "
        f"it is not shown at Emirates/UAE level — it is only for Loc 3 and further, in "
        f"Dubai and Abu Dhabi."
    )


def test_widget_not_shown_with_multiple_locations(properties_screen):
    """Hard rule: no TruBroker widget once more than one location is applied.

    Applies two Loc 3 areas, either of which could legitimately show the widget alone —
    so if it appears here, multiplicity is the only explanation.
    """
    results = properties_screen.search_locations(LOC3_DUBAI, SECOND_LOCATION)
    observed = results.observed_widget_order()
    print(f"\n  locations: {LOC3_DUBAI} + {SECOND_LOCATION}")
    print(f"  widgets seen: {[n for n, _ in observed]}")

    assert WIDGET not in dict(observed), (
        f"TruBroker widget appeared with two locations applied "
        f"({LOC3_DUBAI} + {SECOND_LOCATION}). The checklist states it is not shown when "
        f"multiple locations are entered."
    )


def test_widget_position_when_shown_at_loc3(properties_screen):
    """Soft rule: when the widget IS shown at Loc 3, it sits at position 1.

    Skips when absent. That is not a defect: the widget renders the top TruBrokers for
    the location, and a Loc 3 area with none legitimately shows nothing (§16, "only
    inline filters containing data will be visible"). The skip message says which
    location was tried, so a human can decide whether the absence is itself worth a look.
    """
    results = properties_screen.search_locations(LOC3_DUBAI)
    observed = results.observed_widget_order()
    positions = dict(observed)
    print(f"\n  location: {LOC3_DUBAI} (Loc 3, Dubai)")
    print(f"  widgets seen: {observed}")

    if WIDGET not in positions:
        pytest.skip(
            f"TruBroker widget not present for {LOC3_DUBAI!r}. Legal if that location "
            f"currently has no TruBrokers — but if you expect some there, this is worth "
            f"checking by hand. Widgets that did appear: {[n for n, _ in observed]}"
        )

    assert positions[WIDGET] <= 1, (
        f"TruBroker widget appeared after ~{positions[WIDGET]} listings; the checklist "
        f"documents position 1 (after the 1st listing). Card counts across scrolls are "
        f"best-effort — confirm by eye before filing."
    )
