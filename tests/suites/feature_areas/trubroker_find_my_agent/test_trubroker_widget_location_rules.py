"""TruBroker LPV widget — location visibility rules.

docs/REGRESSION-CHECKLIST.md, "TruBroker™ & Find My Agent":

  * not shown at Emirates / UAE level
  * shown for Loc 3 and further, in Dubai and Abu Dhabi only
  * visible to agents and end users, logged in or out
  * **not** shown when multiple locations are entered

PRODUCTION DATA CONSTRAINT
--------------------------
Every search here uses `TEST_LOCATION` ("Al Napoca") — the QA team's own sanctioned test
location (§5). An earlier version of this file searched "Dubai", "Business Bay" and
"Dubai Marina", which browses real brokerages' live inventory on a production app. That
was wrong and is corrected here.

**This costs coverage, and the tradeoff should be visible rather than hidden.** Two of
the four rules cannot be checked from a single sanctioned location:

  * "not shown at Emirates level" needs an emirate-level (Loc 1) search.
  * "not shown with multiple locations" needs a second location.

Both are read-only searches that create no data, so they *could* be enabled if the QA
lead decides an unfiltered or emirate-level search is acceptable. Until then they skip
with that decision named, rather than silently searching somewhere they should not.

The rule that CAN be checked here — position when shown — is checked, and it is checked
as a soft rule: §16 states only widgets containing data are visible, so an absent widget
at a test location with no TruBrokers is not a defect.
"""
from __future__ import annotations

import pytest

from test_data import TEST_LOCATION

WIDGET = "TruBroker"


@pytest.fixture(autouse=True)
def _restore_default_location(properties_screen):
    """Clear the applied location after every test in this module.

    This is the only module that applies a location filter, and the app persists the
    last search — so without this it silently changes what every later test sees. That
    is not hypothetical: it caused seven unrelated failures on 2026-08-11, including the
    emirates check, because Popular Locations shows child locations of whatever is
    applied (checklist §13).

    `conftest.properties_screen` also resets on the way in, which covers tests that come
    after. This runs on the way out, which additionally covers tests that use only
    `home_screen` and never touch the LPV fixture at all. Cleaning up after yourself is
    cheaper than every other test defending against you.
    """
    yield
    properties_screen.ensure_default_location()


def test_widget_position_when_shown_at_test_location(properties_screen):
    """When the TruBroker widget is shown, it sits at position 1.

    Skips when absent. The widget renders the top TruBrokers for a location, so a test
    location with none legitimately shows nothing — failing there would be failing on
    live inventory rather than on a defect.
    """
    results = properties_screen.search_locations(TEST_LOCATION)
    observed = results.observed_widget_order()
    positions = dict(observed)
    print(f"\n  location: {TEST_LOCATION!r} (sanctioned test location)")
    print(f"  widgets seen: {observed}")

    if WIDGET not in positions:
        pytest.skip(
            f"TruBroker widget not present for {TEST_LOCATION!r}. Legal per checklist "
            f"§16 if that location has no TruBrokers. Widgets that did appear: "
            f"{[n for n, _ in observed]}"
        )

    assert positions[WIDGET] <= 1, (
        f"TruBroker widget appeared after ~{positions[WIDGET]} listings; the checklist "
        f"documents position 1 (after the 1st listing). Card counts across scrolls are "
        f"best-effort — confirm by eye before filing."
    )


@pytest.mark.skip(
    reason="Rule: 'TruBroker widget is not shown at Emirates/UAE level'. Checking it "
           "requires an emirate-level (Loc 1) search, i.e. searching outside the "
           "sanctioned test location 'Al Napoca'. The search itself is read-only and "
           "creates no data, but the standing instruction is to use strictly the "
           "checklist §5 test data on production. Needs the QA lead's call: allow an "
           "emirate-level read-only search, or accept this rule as manual. "
           "NOTE (OBSERVED 2026-08-11, build 15.7.2): on an LPV with NO location applied "
           "— i.e. UAE level — cl_trubroker_container WAS present at position 1. If an "
           "unfiltered search counts as 'UAE level', that is a candidate defect against "
           "this exact rule and is worth a manual look."
)
def test_widget_not_shown_at_emirate_level(properties_screen):
    raise NotImplementedError


@pytest.mark.skip(
    reason="Rule: 'TruBroker widget is not shown when multiple locations are entered'. "
           "Checking it requires applying a SECOND location alongside 'Al Napoca', which "
           "means searching a location outside the sanctioned test data. Read-only, but "
           "same standing instruction — needs the QA lead's call. If a second sanctioned "
           "test location exists, name it in tests/test_data.py and this becomes a real "
           "test immediately."
)
def test_widget_not_shown_with_multiple_locations(properties_screen):
    raise NotImplementedError
