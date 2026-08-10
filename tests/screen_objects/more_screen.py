"""More screen — hub for Sign In, Activity Log, Favourites, Find My Agent.

Locators confirmed two ways: this session's own crawl, and independently by the
pre-existing appium/ suite (see docs/DECISIONS.md D-019) — both agree on these ids.
"""
from __future__ import annotations

from .base import BaseScreen


class MoreScreen(BaseScreen):
    BOTTOM_NAV_MORE = "com.bayut.bayutapp:id/bottom_nav_more_id"
    ACTIVITY_LOG_CARD = "com.bayut.bayutapp:id/cv_activity_log"
    SIGN_IN_BUTTON = "com.bayut.bayutapp:id/more_user_btn"
    LOGGED_IN_USER_CONTAINER = "com.bayut.bayutapp:id/logged_in_user_container"

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.BOTTOM_NAV_MORE)

    def is_signed_in(self, timeout: int = 5) -> bool:
        """Authoritative, scroll-free sign-in signal — OBSERVED 2026-08-10, build
        15.7.2 (1272): the account row at the very top of More swaps entirely between
        the two states, so exactly one of these is ever present, no scrolling needed:
          * signed OUT -> SIGN_IN_BUTTON (more_user_btn, "Sign In") is present
          * signed IN  -> LOGGED_IN_USER_CONTAINER ("Hi, <name>" + "View Profile" row)
            is present instead, and SIGN_IN_BUTTON does not exist in the tree at all

        This is the "if no sign in/sign up button, already signed in" check — reading
        the actual top-level control rather than inferring state from "Log Out" being
        scrolled into view further down the More menu (still needed to physically tap
        Log Out, but not to decide whether to bother).

        Raises if neither element shows up within `timeout` — an unrecognized state
        (e.g. the screen is still loading) is a real unknown, not something to guess
        at (CLAUDE.md: never guess).
        """
        if self.is_present(resource_id=self.LOGGED_IN_USER_CONTAINER, timeout=timeout):
            return True
        if self.is_present(resource_id=self.SIGN_IN_BUTTON, timeout=timeout):
            return False
        raise AssertionError(
            "neither the signed-in account row (logged_in_user_container) nor the "
            "Sign In button (more_user_btn) is present on More — can't determine "
            "sign-in state; refusing to guess"
        )

    # --- §21 More screen sections -----------------------------------------
    # Labels come from the checklist itself, so text matching is legitimate here: the
    # checklist specifies the wording. Still English-only — the Localization section
    # (§23) covers the other three locales and is blocked on the locale-switch decision.
    SECTIONS_UNSIGNED: tuple[str, ...] = (
        "Activity Log", "Sell My Property", "Dubai Transactions", "TruEstimate",
        "Find my Agent", "Favourites", "Floor Plans", "Language", "Manage Alerts",
        "Notification Center", "Blog", "Guides", "Settings", "Contact Us",
        "About Us", "Privacy Policy",
    )
    SECTIONS_SIGNED_IN: tuple[str, ...] = SECTIONS_UNSIGNED + ("Log Out",)

    # Present in the checklist but time-limited or role-scoped, so absence is reported
    # rather than failed: a 2024 awards promo may simply have ended, and agent-only
    # rows depend on the account type.
    SECTIONS_ADVISORY: tuple[str, ...] = (
        "Bayut Awards 2024",        # dated promo — may have been retired
        "View Profile",             # agent accounts only
        "My Transactions Reports",  # agents only
        "Edit Profile",             # signed-in only
        "My TruEstimate Reports",   # signed-in only
    )

    def visible_section_labels(self, max_swipes: int = 12) -> list[str]:
        """Scroll More top-to-bottom and collect every visible text label, in order."""
        self.swipe_down_to_top()
        labels: list[str] = []
        for _ in range(max_swipes):
            for el in sorted((e for e in self.current_elements() if e.bounds),
                             key=lambda e: e.bounds[1]):
                text = (el.text or el.content_desc or "").strip()
                if text and text not in labels:
                    labels.append(text)
            before = len(labels)
            self.swipe_up()
            if len(labels) == before:
                break  # nothing new came into view; we are at the bottom
        return labels

    def missing_sections(self, expected: tuple[str, ...],
                         labels: list[str] | None = None) -> list[str]:
        """Which expected sections are not present. Case- and spacing-insensitive."""
        found = labels if labels is not None else self.visible_section_labels()
        norm = {"".join(l.lower().split()) for l in found}
        return [s for s in expected if "".join(s.lower().split()) not in norm]

    def open_activity_log(self):
        from .activity_log_screen import ActivityLogScreen
        self.safe_tap(resource_id=self.ACTIVITY_LOG_CARD)
        return ActivityLogScreen(self.driver, self.safety_policy, self.timeout)

    def open_favourites(self):
        from .favourites_screen import FavouritesScreen
        self.safe_tap(text="Favourites")
        return FavouritesScreen(self.driver, self.safety_policy, self.timeout)

    def open_sign_in(self):
        """Lands on the sign-in method screen (Continue with Email / Google /
        Facebook / WhatsApp / Magic Link) — confirmed live this session. Stops here,
        one level above the old suite's assumption, so a caller chooses a method
        explicitly (e.g. .continue_with_email()) rather than it being baked in."""
        from .sign_in_screen import SignInMethodScreen
        self.safe_tap(resource_id=self.SIGN_IN_BUTTON)
        return SignInMethodScreen(self.driver, self.safety_policy, self.timeout)

    def open_find_my_agent(self):
        """"Find my Agent" sits far down the More menu — needs a scroll, not a plain
        tap (confirmed by both this session's crawl and the ported suite)."""
        from .find_my_agent_hub_screen import FindMyAgentHubScreen
        self.safe_tap_scrolled_text("Find my Agent", max_swipes=10)
        return FindMyAgentHubScreen(self.driver, self.safety_policy, self.timeout)
