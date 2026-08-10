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

    #: The More menu's own container. Unlike BOTTOM_NAV_MORE this exists ONLY on More.
    MORE_ITEMS_LIST = "com.bayut.bayutapp:id/more_items_list"

    def is_displayed(self, timeout: int = 10) -> bool:
        """True only when the More screen itself is up.

        Previously this checked BOTTOM_NAV_MORE — but the bottom nav is present on
        *every* bottom-nav screen, so it returned True while still on Home, before the
        tap had landed. Callers then read More-specific state too early: `is_signed_in()`
        found neither the Sign In button nor the account row and raised its
        "can't determine sign-in state" error, which looked like a real finding and was
        actually a race. `more_items_list` exists only on More.
        """
        return self.is_present(resource_id=self.MORE_ITEMS_LIST, timeout=timeout)

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
    # Rows are LOCATED by resource-id (`more_item_parent` wrapping `item_text`); their
    # text is then read as an assertion *value*. That distinction matters: locating by
    # label would break in ar/ru/zh, but the checklist item genuinely is "does the More
    # screen offer these sections", and a section is named by its label.
    #
    # LOCATOR-QUALITY FINDING: every row shares the same two ids, so there is no way to
    # identify *which* row is which except by its text. That belongs in the testID ask —
    # a per-row id (more_item_activity_log, more_item_settings, ...) would make this
    # locale-proof. Recorded in context/locator-quality.md.
    ROW_CONTAINER = "com.bayut.bayutapp:id/more_item_parent"
    ROW_LABEL = "com.bayut.bayutapp:id/item_text"
    ACTIVITY_CARD_TITLE = "com.bayut.bayutapp:id/tv_my_activity"
    APP_VERSION = "com.bayut.bayutapp:id/tv_app_version"

    # OBSERVED 2026-08-10, build 15.7.2 (1272), signed out, en-GB. Corrected against the
    # live screen: the app says "My Activity", not the checklist's "Activity Log", and
    # TruEstimate carries a ™ — hence the symbol-stripping in _normalise().
    SECTIONS_UNSIGNED: tuple[str, ...] = (
        "My Activity", "Sell My Property", "Dubai Transactions", "TruEstimate",
        "TruEstimate Portfolio", "Favourites", "Saved Searches", "Find my Agent",
        "Floor Plans", "Language", "Manage Alerts", "Notification Center",
        "Blog", "Guides", "Settings", "Contact Us", "About Us", "Privacy Policy",
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

    @staticmethod
    def _normalise(label: str) -> str:
        """Fold away casing, whitespace and decorative symbols.

        The app renders "TruEstimate™‎" — a trademark sign plus a left-to-right
        mark, the latter invisible and easy to miss when eyeballing a diff. Comparing
        raw strings against a checklist written without them fails for no real reason.
        """
        import re
        return re.sub(r"[^a-z0-9]", "", label.lower())

    def visible_section_labels(self, max_swipes: int = 12) -> list[str]:
        """Scroll More top-to-bottom and collect the section labels, in order.

        Reads only elements located by resource-id — the menu rows (`item_text`) and the
        Activity card's own title (`tv_my_activity`) — rather than hoovering up every
        string on screen. That keeps the promotional blurb, the version footer and the
        bottom-nav labels out of the result.
        """
        self.swipe_down_to_top()
        wanted = {self.ROW_LABEL, self.ACTIVITY_CARD_TITLE}
        labels: list[str] = []
        for _ in range(max_swipes):
            # Count BEFORE collecting, not after. The previous version took `before`
            # after the collection loop and compared it to the same unchanged list, so
            # the two were always equal and it stopped after a single screenful —
            # reporting 10 of the 18 sections as missing when every one was present.
            before = len(labels)
            rows = [e for e in self.current_elements()
                    if e.resource_id in wanted and e.text and e.bounds]
            for el in sorted(rows, key=lambda e: e.bounds[1]):
                text = el.text.strip()
                if text and text not in labels:
                    labels.append(text)
            if len(labels) == before and before:
                break  # a full screenful added nothing new; we are at the bottom
            self.swipe_up()
        return labels

    def missing_sections(self, expected: tuple[str, ...],
                         labels: list[str] | None = None) -> list[str]:
        """Which expected sections are not present, ignoring case/spacing/symbols."""
        found = labels if labels is not None else self.visible_section_labels()
        norm = {self._normalise(l) for l in found}
        return [s for s in expected if self._normalise(s) not in norm]

    def open_activity_log(self):
        """The My Activity card sits at the top of More, above the menu rows.

        Scrolls to top first: More retains its scroll position between visits, so after
        any test that scrolled down to reach a lower row (Manage Alerts, Find my Agent)
        the card is off-screen and a plain tap times out. Cheap, and a no-op when
        already at the top.
        """
        from .activity_log_screen import ActivityLogScreen
        self.swipe_down_to_top()
        self.safe_tap(resource_id=self.ACTIVITY_LOG_CARD)
        return ActivityLogScreen(self.driver, self.safety_policy, self.timeout)

    def scroll_to_row(self, label: str, max_swipes: int = 12) -> bool:
        """Bring a More row into view, always starting from the top.

        More retains its scroll position between visits, and UiAutomator2's
        scrollIntoView only searches *forward* — so a row above the current position is
        never found, and D-024 records that scrollIntoView can even return the wrong
        element rather than failing cleanly. Resetting to the top first makes the search
        deterministic regardless of what the previous test left behind.
        """
        self.swipe_down_to_top()
        for _ in range(max_swipes):
            if self.is_present(text=label, timeout=1):
                return True
            self.swipe_up()
        return self.is_present(text=label, timeout=1)

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
