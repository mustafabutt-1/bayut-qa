"""§4 Sign in / Sign up — docs/REGRESSION-CHECKLIST.md. CONSEQUENTIAL, opt-in only.

Direct email/password sign-in, confirmed live this session (More -> Sign In ->
Continue with Email -> "Welcome to Bayut.com" form -> Log in). Supersedes the ported
suite's cached-account/autofill-dependent flow (docs/DECISIONS.md D-019) with a
straightforward one that doesn't depend on the device's own saved credential state.

Isolated here, not in the default gated suite, because signing out first is required —
and `Log Out` is BLOCK-LOGOUT in the shared crawl_safety policy, permanently and
correctly (CLAUDE.md: "destroys session, kills the crawl"). Logout goes through
`deliberate_tap()`, never `safe_tap()`. The "Continue with Email" button and the "Log
in" submit button both go through the normal `safe_tap()` gate — see D-025 and
ALLOW-BAYUT-SIGNIN-EMAIL / ALLOW-BAYUT-LOGIN-SUBMIT in context/crawl-allowlist.yaml for
why each is safe to allow. Typing the email/password never taps the input fields at all
(see email_login_screen.py) — et_email_field correctly stays BLOCK-LEAD-EMAIL, and this
flow simply doesn't need to tap it.

Both consequential actions are guarded by an explicit sign-in-state check first, via
`MoreScreen.is_signed_in()` — OBSERVED 2026-08-10: the account row at the very top of
More swaps entirely between guest and authenticated state (SIGN_IN_BUTTON vs
LOGGED_IN_USER_CONTAINER), so this reads directly with no scrolling required:
  - Before logout: if no Sign In button is showing (i.e. is_signed_in() is True),
    proceed; if it IS showing, already logged out — nothing to do.
  - Before sign-in: if no logged-in account row is showing (i.e. is_signed_in() is
    False), proceed; verified again immediately after `_ensure_logged_out` (which
    already asserts this itself) — defense-in-depth so this test never proceeds to
    "sign in" while secretly still authenticated as something else.

Locating and tapping the physical "Log Out" row still needs a scroll (it sits below
the fold in the More menu) — manual swipe + is_present, not UiAutomator2's
scrollIntoView, see D-024 for why — but that scroll only ever happens once
is_signed_in() has already confirmed there's a reason to.

Test account: TEST_ACCOUNT_PORTFOLIO_EMAIL — the QA team's own
sectorlabs.ro test account from docs/REGRESSION-CHECKLIST.md. TEST_ACCOUNT_PORTFOLIO_PASSWORD
must also be set in .env for this test — it is not invented here, and is left blank in
.env.example/.env until supplied.

Requires RUN_CONSEQUENTIAL_TESTS=1 to run at all — a real environment check, not just a
folder/marker convention, so `pytest tests/` alone can never trigger this.
"""
from __future__ import annotations

import os

import pytest

from screen_objects.consequential import deliberate_tap

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CONSEQUENTIAL_TESTS") != "1",
    reason="Consequential test (signs a real account out and back in). "
           "Set RUN_CONSEQUENTIAL_TESTS=1 to run deliberately.",
)

ACCOUNT_EMAIL = os.environ.get("TEST_ACCOUNT_PORTFOLIO_EMAIL", "")
ACCOUNT_PASSWORD = os.environ.get("TEST_ACCOUNT_PORTFOLIO_PASSWORD", "")


def _swipe_to_find_text(more_screen, text: str, max_swipes: int = 12) -> bool:
    """Manually swipe up a bounded number of times, re-checking with our own
    is_present() (a plain, un-scrolled visibility check) after each swipe — instead of
    delegating to UiAutomator2's own `scrollIntoView`.

    Confirmed live: `scrollIntoView` can complete without raising even when the target
    text was never actually present (e.g. the account was already signed out and "Log
    Out" doesn't exist at all), returning some other element instead of a clean
    not-found signal. That's exactly the wrong failure mode for a check gating a
    consequential tap — is_present()/wait_for() have been reliable everywhere else
    this session, so this rebuilds the same "scroll until visible" behaviour on top of
    them rather than trusting UiAutomator2's own matching-while-scrolling.

    Only used now to physically locate the "Log Out" row for tapping — callers decide
    *whether* to bother via the fast MoreScreen.is_signed_in() check first."""
    if more_screen.is_present(text=text, timeout=1):
        return True
    for _ in range(max_swipes):
        more_screen.swipe_up()
        if more_screen.is_present(text=text, timeout=1):
            return True
    return False


def _ensure_logged_out(more_screen) -> None:
    """(a) 'if no logout button, already logged out': is_signed_in()==False means the
    Sign In button is showing at the top of More, i.e. there's no Log Out to tap at
    all — nothing to do. Only when is_signed_in()==True do we scroll to find and tap
    the real Log Out row."""
    if not more_screen.is_signed_in():
        return

    driver = more_screen.driver
    found = _swipe_to_find_text(more_screen, "Log Out", max_swipes=12)
    assert found, (
        "MoreScreen.is_signed_in() just confirmed a signed-in state, but scrolling to "
        "find the 'Log Out' row failed — something changed between the two checks, or "
        "the row is further down than max_swipes covers"
    )
    log_out_el = more_screen.wait_for(text="Log Out", timeout=3)
    deliberate_tap(driver, log_out_el, reason="test setup: force a known logged-out "
                    "state before exercising sign-in", evidence_tag="sign-in-logout")

    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    yes_el = WebDriverWait(driver, 10).until(
        lambda d: d.find_element(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Yes")')
    )
    deliberate_tap(driver, yes_el, reason="confirm the logout dialog opened above",
                    evidence_tag="sign-in-logout-confirm")
    more_screen.swipe_down_to_top()
    more_screen.swipe_down_to_top()

    assert not more_screen.is_signed_in(), (
        "expected a logged-out state (Sign In button present) after confirming Log "
        "Out, but the signed-in account row is still showing — logout did not take "
        "effect"
    )


def test_sign_in_with_email_password(home_screen):
    assert ACCOUNT_EMAIL, "TEST_ACCOUNT_PORTFOLIO_EMAIL must be set in .env"
    assert ACCOUNT_PASSWORD, (
        "TEST_ACCOUNT_PORTFOLIO_PASSWORD must be set in .env for this test — "
        "not invented here, ask whoever owns the sectorlabs.ro test account"
    )
    more = home_screen.open_more()

    _ensure_logged_out(more)
    # (b) 'if no sign in/sign up button, already signed in': is_signed_in() reads the
    # same top-level account row — False means the Sign In button is actually showing,
    # so it's safe to proceed. Defense-in-depth on top of _ensure_logged_out's own
    # check, so this test never proceeds to "sign in" while secretly still
    # authenticated as something else.
    assert not more.is_signed_in(), (
        "expected to already be signed out (Sign In button present) before testing "
        "sign-in; refusing to proceed while still authenticated as something else"
    )

    method_screen = more.open_sign_in()
    assert method_screen.is_displayed()
    email_login = method_screen.continue_with_email()
    assert email_login.is_displayed()
    email_login.login_with_email_password(ACCOUNT_EMAIL, ACCOUNT_PASSWORD)

    # Wherever login lands (More again, Home, a confirmation screen — not yet
    # observed live), re-navigate to More explicitly before checking, rather than
    # assuming `more`'s screen position is still valid.
    more_after = home_screen.open_more()
    assert more_after.is_signed_in(), (
        "expected a signed-in state (account row present in More) after login"
    )
