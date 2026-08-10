"""§10 Home screen sections and banners — docs/REGRESSION-CHECKLIST.md.

The checklist lists what Home must contain: header tabs, TruBroker banner, Seller leads
banner, banners for TruEstimate / BayutGPT / Dubai Transactions / Search 2.0, Continue
last search / Recent Searches, Saved Searches, Favourites, Popular, Lookup Nearby
Locations, Blogs, and the bottom nav.

`test_home_screen.py` already covers the header tabs, Buy/Rent, the search bar and the
bottom nav. This file covers the scrollable body — the banners and content rails.

Everything is located by **resource-id**, never by label, so it survives ar/ru/zh.
Sections with no observed id are reported as *not checkable* rather than being asserted
absent, because "we have no locator" and "the app is missing it" are different findings
and conflating them would file a false defect.
"""
from __future__ import annotations


def test_home_sections_present(home_screen):
    """Every Home section with a known resource-id is reachable by scrolling.

    Also covers the checklist's "Verify the TruBroker flow from the Home screen too" —
    the TruBroker banner is one of the sections asserted here. A separate test for just
    that banner existed briefly and was removed: it re-scrolled the whole Home screen
    (up to 12 swipes) to assert a strict subset of what this already asserts, which is
    two minutes of device time per run for no extra signal.
    """
    found = home_screen.sections_present()
    unresolved = home_screen.unresolved_sections()

    print("\n  sections resolved by resource-id:")
    for name, ok in found.items():
        print(f"    {'FOUND  ' if ok else 'MISSING'}  {name}")
    if unresolved:
        print(f"  NOT CHECKABLE (no resource-id ever observed): {unresolved}")

    missing = [n for n, ok in found.items() if not ok]
    assert not missing, (
        f"Home is missing section(s) that have a known resource-id: {missing}.\n"
        f"These were observed on build 15.7.2 (1272), so their absence is a real change "
        f"— either a defect or a deliberate removal worth confirming.\n"
        f"Sections with no known id, not asserted either way: {unresolved}"
    )
