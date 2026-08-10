"""Sign-in method screen + email/password login form.

Locators confirmed live this session (real navigation, "Welcome to Bayut.com" screen —
supersedes the ported suite's untested cached-account/autofill assumptions for this
flow). `EMAIL_FIELD` deliberately never goes through `safe_tap` — see the allowlist
comment on ALLOW-BAYUT-LOGIN-SUBMIT for why the plain "email field" stays BLOCK
(BLOCK-LEAD-EMAIL) and why that's correct, unlike the "Continue with Email" button.
"""
from __future__ import annotations

from .base import BaseScreen


class SignInMethodScreen(BaseScreen):
    """The method-picker screen (Continue with Email / Google / Facebook / WhatsApp /
    Magic Link)."""
    CONTINUE_WITH_EMAIL = "com.bayut.bayutapp:id/fl_continue_with_email"
    CLOSE = "com.bayut.bayutapp:id/iv_close"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.CONTINUE_WITH_EMAIL)

    def continue_with_email(self):
        """Taps "Continue with Email". If the device has a cached recent login,
        Keycloak shows a "previously logged in" interstitial first instead of the
        blank form directly — OBSERVED 2026-08-10, see docs/DECISIONS.md D-027. This
        transparently taps through "Log in with another account" there too, since this
        suite always wants the real, freshly-typed-credentials form, never the
        device-cached SSO continue path. Returns EmailLoginScreen either way, so
        callers don't need to know which branch happened."""
        from .cached_login_screen import CachedLoginScreen
        from .email_login_screen import EmailLoginScreen
        self.safe_tap(resource_id=self.CONTINUE_WITH_EMAIL)
        cached = CachedLoginScreen(self.driver, self.safety_policy, self.timeout)
        if cached.is_displayed():
            return cached.login_with_another_account()
        return EmailLoginScreen(self.driver, self.safety_policy, self.timeout)


# Backward-compatible alias — screen_objects/more_screen.py's open_sign_in() lands here.
SignInScreen = SignInMethodScreen
