"""Sanctioned production test data — the ONLY data any test may touch.

Source: docs/REGRESSION-CHECKLIST.md §5, given directly by the QA lead.

    Test Location : "Al Napoca"
    Test Agency   : "Explorer Real Estate"
    Test Portfolio account: $TEST_ACCOUNT_PORTFOLIO_EMAIL / _PASSWORD

**Why this file exists.** The app under test is production. Every search, every listing
opened and every agency touched should be ours, not a paying customer's. A test that
searches "Dubai Marina" is browsing a real brokerage's live inventory; a test that
contacts anyone outside Explorer Real Estate sends a real, billable lead.

Import from here. Do not hardcode a location or agency name in a test — that is how the
one exception creeps in six months from now.

Credentials are read from the environment and are **never** written into this repo. The
non-secret values (a location name, an agency name) carry documented defaults so the
suite still runs on a fresh clone, but they can be overridden in `.env` too.
"""
from __future__ import annotations

import os

#: The only location tests may search. Overridable via .env for a future environment.
TEST_LOCATION: str = os.environ.get("LEAD_TEST_LOCATION", "Al Napoca")

#: The only agency whose listings may be opened or contacted. Mirrored in
#: tools/crawl_safety.py as LEAD_TEST_AGENCIES — the guard enforces it at tap time,
#: this constant keeps tests pointed at it in the first place.
TEST_AGENCY: str = (os.environ.get("LEAD_TEST_AGENCY")
                    or os.environ.get("TEST_LEAD_AGENCY_NAME")
                    or "Explorer Real Estate")

#: Portfolio/test account. No default: a missing credential must fail loudly, never
#: silently fall back to some other account.
TEST_ACCOUNT_EMAIL: str = os.environ.get("TEST_ACCOUNT_PORTFOLIO_EMAIL", "")
TEST_ACCOUNT_PASSWORD: str = os.environ.get("TEST_ACCOUNT_PORTFOLIO_PASSWORD", "")


def require_account() -> tuple[str, str]:
    """Return the test account, or fail with an actionable message.

    Never invents a credential and never falls back to another account.
    """
    if not TEST_ACCOUNT_EMAIL or not TEST_ACCOUNT_PASSWORD:
        raise AssertionError(
            "TEST_ACCOUNT_PORTFOLIO_EMAIL and TEST_ACCOUNT_PORTFOLIO_PASSWORD must both "
            "be set in .env (gitignored). See docs/REGRESSION-CHECKLIST.md §5 for which "
            "account, and ask whoever owns the sectorlabs.ro test accounts for the "
            "value — it is deliberately not stored in this repo."
        )
    return TEST_ACCOUNT_EMAIL, TEST_ACCOUNT_PASSWORD
