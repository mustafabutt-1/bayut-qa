"""Email/password login form ("Welcome to Bayut.com") — locators confirmed live this
session by actually navigating here (Continue with Email from the sign-in method
screen). Real resource-ids, not the ported suite's untested guesses.
"""
from __future__ import annotations

from .base import BaseScreen


class EmailLoginScreen(BaseScreen):
    EMAIL_FIELD = "com.bayut.bayutapp:id/et_email_field"
    PASSWORD_FIELD = "com.bayut.bayutapp:id/et_password_field"
    LOGIN_BUTTON = "com.bayut.bayutapp:id/tv_login_button"
    FORGOT_PASSWORD = "com.bayut.bayutapp:id/tv_forgot_password"
    ONE_TIME_LINK_BUTTON = "com.bayut.bayutapp:id/tv_one_time_link_button"
    SIGN_UP_LINK = "com.bayut.bayutapp:id/tv_sign_up"
    CLOSE = "com.bayut.bayutapp:id/iv_close"

    def is_displayed(self, timeout: int | None = None) -> bool:
        """Default timeout is the screen's own (15s), not is_present()'s usual 3s —
        this form sits behind the same slow Keycloak/WebView activity render as
        CachedLoginScreen (see its docstring and docs/DECISIONS.md D-027)."""
        return self.is_present(resource_id=self.EMAIL_FIELD, timeout=timeout or self.timeout)

    def login_with_email_password(self, email: str, password: str):
        """Typing never goes through safe_tap — send_keys() focuses the field itself,
        no preliminary tap needed. This deliberately avoids et_email_field's
        BLOCK-LEAD-EMAIL classification (correctly not exempted — see D-025/
        ALLOW-BAYUT-LOGIN-SUBMIT's comment in context/crawl-allowlist.yaml): a bare
        "email field" can't be distinguished from a lead-form's own email field by
        pattern alone, so it stays gated: this path just never needs to tap it."""
        self.wait_for(resource_id=self.EMAIL_FIELD).send_keys(email)
        self.wait_for(resource_id=self.PASSWORD_FIELD).send_keys(password)
        self.safe_tap(resource_id=self.LOGIN_BUTTON)
