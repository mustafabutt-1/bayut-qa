"""§16 Listings page (LPV) inline widgets — docs/REGRESSION-CHECKLIST.md.

The checklist states two things that shape every test here:

  1. "Only inline filters containing data will be visible."
     So **absence is not a defect.** No test asserts that a given widget exists.
  2. Documented positions: TruBroker after listing 1, BayutGPT after 3,
     TruEstimate after 7, Dubai Transactions after 10.
     So the assertable property is their **relative order**.

Why order and not absolute position: counting "after the Nth listing" across scrolls
means de-duplicating cards that reappear between screenfuls, and two units in the same
tower can share a price, so the count drifts. Order cannot drift that way. The observed
counts are printed as evidence so a human can audit them, per CLAUDE.md.

FIRST RUN: these match on visible text, because the crawl's page-source dumps are
gitignored and the widget container ids have never been observed here. The report each
test prints includes what it matched — replace INLINE_WIDGET_MARKERS with resource-ids
from that output, then these become locale-proof.
"""
from __future__ import annotations

import pytest


def test_inline_widgets_appear_in_documented_order(properties_screen):
    """Widgets present on the LPV appear in the checklist's documented order.

    Skips rather than fails when fewer than two documented widgets are visible —
    with one or zero there is no order to verify, and the checklist explicitly
    permits them to be absent.
    """
    observed = properties_screen.observed_widget_order()
    print("\n  observed inline widgets (name, listing cards seen before it):")
    for name, position in observed:
        print(f"    {name:<28} after ~{position} listing(s)")
    if not observed:
        print("    (none found — legal per the checklist if none had data)")

    documented = [n for n, _ in observed
                  if n in properties_screen.DOCUMENTED_WIDGET_ORDER]
    if len(documented) < 2:
        pytest.skip(
            f"only {len(documented)} documented widget(s) visible "
            f"({documented or 'none'}) — nothing to order. Legal per the checklist: "
            f"'only inline filters containing data will be visible'."
        )

    expected = [n for n in properties_screen.DOCUMENTED_WIDGET_ORDER if n in documented]
    assert documented == expected, (
        f"inline widgets appeared in the wrong order.\n"
        f"  observed : {documented}\n"
        f"  expected : {expected}\n"
        f"Checklist §16 documents TruBroker after listing 1, BayutGPT after 3, "
        f"TruEstimate after 7, Dubai Transactions after 10."
    )


def test_alert_me_cta_is_not_tappable_on_production(properties_screen):
    """The 'Alert Me of New Properties' CTA must be refused, not tapped.

    Checklist §16 lists it as an inline item, and §4 notes sign-up is verified through
    it (Implicit Register). Tapping it on production creates a real alert against a real
    account and starts recurring email/push — PROD-BLOCK-SAVE-SEARCH. This test asserts
    the guard holds rather than exercising the CTA.

    Skips when the CTA is absent: it is data-dependent like every other inline item.
    """
    observed = dict(properties_screen.observed_widget_order())
    if "Alert Me of New Properties" not in observed:
        pytest.skip("'Alert Me of New Properties' CTA not present on this result set")
    properties_screen.assert_blocked(text="Alert Me of New Properties")


def test_save_search_is_blocked_on_production(properties_screen):
    """The LPV Save-search control must be refused on production.

    §19 Saved Searches is manual-only under the guardrails; this proves the reason —
    the control is gated, not merely untested. Uses the resource-id already proven by
    the live session (save_text_tb_rev_1).
    """
    properties_screen.assert_blocked(resource_id=properties_screen.SAVE_SEARCH)
