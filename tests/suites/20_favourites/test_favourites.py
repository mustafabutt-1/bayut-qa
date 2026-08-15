"""§20 Favourites — docs/REGRESSION-CHECKLIST.md.

Presence-and-refusal only. Favouriting writes real account data on production
(`PROD-BLOCK-FAVOURITE`, docs/GUARDRAILS.md) — this file proves the checklist item
"Favourite functionality" exists as a control and that the safety guard genuinely
refuses it, without ever creating a real favourite. The consequential half (actually
favouriting a listing and confirming it appears/persists) lives in
`consequential/test_favourites.py`, gated behind `RUN_CONSEQUENTIAL_TESTS=1`.

`favourite_cb` used to fall through to ALLOW via `ALLOW-NAV-TABS`'s generic "favourites"
word list — word-normalisation turned "favourite_cb" into "favourite cb" for matching,
creating a real `\\b` boundary the raw underscored id never had. Fixed in
`tools/crawl_safety.py`'s `PROD-BLOCK-FAVOURITE` pattern; see docs/DECISIONS.md D-041.
"""
from __future__ import annotations


def test_favourite_checkbox_present_and_blocked(properties_screen):
    price, _center = properties_screen.locate_favourite_checkbox(0)
    assert price is not None, "could not read the first listing's price"
    properties_screen.assert_blocked(resource_id=properties_screen.FAVOURITE_CHECKBOX)
