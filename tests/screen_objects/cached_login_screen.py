"""Keycloak "previously logged in" interstitial — OBSERVED 2026-08-10 (KeyCloakAuthActivity).

Appears after "Continue with Email" whenever the device already has a cached recent
login (e.g. from a prior run of this suite): "Welcome to Bayut.com" / "You have
previously logged in. Continue from where you left off?", with the cached account in
`rv_recent_logins` and "Log in with another account" (fl_login_button) to bypass it.
This suite always takes that path — it types real credentials fresh into the blank form
(EmailLoginScreen), never the device-cached SSO continue — see docs/DECISIONS.md D-027.
"""
from __future__ import annotations

from .base import BaseScreen


class CachedLoginScreen(BaseScreen):
    TITLE = "com.bayut.bayutapp:id/tv_title"
    LOGIN_ANOTHER_ACCOUNT = "com.bayut.bayutapp:id/fl_login_button"
    CLOSE = "com.bayut.bayutapp:id/iv_close"

    def is_displayed(self, timeout: int | None = None) -> bool:
        """Default timeout is the screen's own (15s, DEFAULT_EXPLICIT_WAIT), not the
        usual is_present() default of 3s — OBSERVED 2026-08-10: KeyCloakAuthActivity
        (Keycloak/WebView-backed) took noticeably longer than 3s to finish rendering
        after the "Continue with Email" tap in live testing, causing this check to read
        False before the interstitial had actually appeared."""
        return self.is_present(resource_id=self.LOGIN_ANOTHER_ACCOUNT,
                                timeout=timeout or self.timeout)

    def login_with_another_account(self):
        from .email_login_screen import EmailLoginScreen
        self.safe_tap(resource_id=self.LOGIN_ANOTHER_ACCOUNT)
        return EmailLoginScreen(self.driver, self.safety_policy, self.timeout)
