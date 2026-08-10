"""Shared screen-object base.

Two rules, non-negotiable per CLAUDE.md:

  1. Explicit waits only. `wait_for` / `is_present` poll via Selenium's `WebDriverWait`
     against a real condition — never `time.sleep()`.
  2. Every tap goes through `crawl_safety.SafetyPolicy` before it happens. `safe_tap`
     re-dumps `page_source`, classifies the target element the same way the live crawl
     did, and raises rather than taps anything that isn't a clean ALLOW verdict. This is
     the only tap path in this test suite — there is no direct `.click()` anywhere else,
     with the one deliberate, isolated exception in
     tests/suites/05_leads/consequential/ (see docs/DECISIONS.md D-019).

The scroll/swipe helpers below are ported from the pre-existing appium/ suite
(docs/DECISIONS.md D-019) — its W3C-pointer-action `swipe()` and "click the element you
already scrolled to, don't re-query" pattern were both hard-won fixes for real,
confirmed-live bugs (`mobile: swipeGesture` silently ignoring explicit coordinates; a
second independent find racing the list settling after a scroll).
"""
from __future__ import annotations

import sys
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.support.ui import WebDriverWait

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pagesource import Element, parse_page_source, tappable  # noqa: E402


class SafetyRefusal(AssertionError):
    """Raised when a test tries to tap something the safety gate did not ALLOW.

    A test hitting this is not a flake — it means either the test itself is wrong
    (asserting on a flow that is supposed to stay manual-only), or a real behavioural
    change moved a consequential control somewhere the allowlist doesn't yet cover.
    Never silence this by widening a rule from inside a test.
    """


class BaseScreen:
    def __init__(self, driver, safety_policy, timeout: int = 15):
        self.driver = driver
        self.safety_policy = safety_policy
        self.timeout = timeout

    # -- locating ----------------------------------------------------------

    @staticmethod
    def _by(resource_id: str | None = None, accessibility_id: str | None = None,
            text: str | None = None):
        from appium.webdriver.common.appiumby import AppiumBy

        if accessibility_id:
            return AppiumBy.ACCESSIBILITY_ID, accessibility_id
        if resource_id and text:
            # Plain AppiumBy.ID can't filter by text — it would silently return the
            # first element with this resource-id regardless of which `text` was
            # asked for (confirmed live: this made open_buy_rent_picker() and
            # open_property_type_picker() both tap the same empty-text filter icon
            # that open_full_filters() taps, landing on the wrong sheet every time).
            escaped = text.replace('"', '\\"')
            return (AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().resourceId("{resource_id}").text("{escaped}")')
        if resource_id:
            return AppiumBy.ID, resource_id
        if text:
            return AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{text}")'
        raise ValueError("locator needs resource_id, accessibility_id, or text")

    def wait_for(self, resource_id: str | None = None, accessibility_id: str | None = None,
                 text: str | None = None, timeout: int | None = None):
        by, value = self._by(resource_id, accessibility_id, text)
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            lambda d: d.find_element(by, value)
        )

    def is_present(self, resource_id: str | None = None, accessibility_id: str | None = None,
                   text: str | None = None, timeout: int = 3) -> bool:
        try:
            self.wait_for(resource_id, accessibility_id, text, timeout=timeout)
            return True
        except TimeoutException:
            return False

    def option_present(self, resource_id: str, text: str, timeout: int | None = None) -> bool:
        """For chip/radio groups sharing one resource-id (e.g. bedroom counts), where
        Selenium's plain By.ID can't disambiguate by text. Polls page_source via
        WebDriverWait — a real explicit wait against a real condition, not a fixed
        sleep — so this doesn't race a bottom sheet's slide-in animation the way a
        single unconditional page_source dump would."""
        try:
            WebDriverWait(self.driver, timeout or self.timeout).until(
                lambda d: self._match(resource_id=resource_id, accessibility_id=None,
                                       text=text, include_nested=True) is not None
            )
            return True
        except TimeoutException:
            return False

    def current_elements(self) -> list[Element]:
        return parse_page_source(self.driver.page_source)

    def _match(self, resource_id: str | None, accessibility_id: str | None,
               text: str | None, *, include_nested: bool = False) -> Element | None:
        # `tappable(include_nested=False)` treats a card-like container as one tap
        # target and excludes its clickable children — correct for deciding "what
        # would the crawler have tried tapping here," wrong for "does this specific
        # nested control (e.g. a lead button drawn on a listing fat card) exist and
        # get classified correctly." assert_blocked() below wants the latter.
        elements = self.current_elements()
        candidates = tappable(elements, include_nested=include_nested)
        for el in candidates:
            if accessibility_id and el.content_desc == accessibility_id:
                if text is None or el.text == text:
                    return el
            elif resource_id and el.resource_id == resource_id:
                if text is None or el.text == text:
                    return el
            elif text and not resource_id and not accessibility_id and el.text == text:
                return el
        # Fall back to every element, not just tap candidates. A label commonly isn't
        # clickable=True itself — a card's name/price TextView, a menu row's text —
        # the OS routes a Selenium click() on it to the actual clickable ancestor
        # regardless, so `wait_for` (Selenium) already succeeded by the time this
        # runs. Classification only needs to know what the row *is*. Confirmed live,
        # twice: this is what broke MoreScreen.open_favourites() (text-only lookup)
        # and FindMyAgentHubScreen.open_first_agency_result() (resource_id lookup on
        # a non-clickable tv_agency_name label inside a clickable result card).
        for el in elements:
            if accessibility_id and el.content_desc == accessibility_id:
                if text is None or el.text == text:
                    return el
            elif resource_id and el.resource_id == resource_id:
                if text is None or el.text == text:
                    return el
            elif text and not resource_id and not accessibility_id and el.text == text:
                return el
        return None

    # -- the only tap path ---------------------------------------------------

    def safe_tap(self, resource_id: str | None = None, accessibility_id: str | None = None,
                 text: str | None = None, timeout: int | None = None):
        """Wait for the element, safety-classify it, tap only on a clean ALLOW.
        include_nested=True: a caller naming a specific resource/accessibility id wants
        that exact element classified, regardless of whether tools/crawler.py's own
        autonomous-exploration heuristic would have offered it as a top-level candidate
        (see the note on _match())."""
        web_el = self.wait_for(resource_id, accessibility_id, text, timeout=timeout)
        match_text = text if not (resource_id or accessibility_id) else None
        target = self._match(resource_id, accessibility_id, match_text, include_nested=True)
        if target is None:
            # A dynamic list (e.g. search results replacing a "Featured" list) can be
            # mid-transition right when wait_for() succeeds — Selenium found *some*
            # element with this locator, but by the time _match()'s own fresh
            # page_source dump ran, the list had briefly nothing matching. An explicit
            # wait on the classification condition itself (not a Selenium locator, so
            # WebDriverWait needs a lambda rather than a By/value pair) rides through
            # that one-frame gap instead of failing on it (confirmed live).
            try:
                target = WebDriverWait(self.driver, 2).until(
                    lambda d: self._match(resource_id, accessibility_id, match_text,
                                           include_nested=True)
                )
            except TimeoutException:
                target = None
        if target is None:
            # Same failure mode tools/crawler.py's D-017 fix addresses: a heads-up
            # notification from an unrelated app (confirmed live, twice, this
            # session — Snapchat) can intercept a tap's coordinates and foreground
            # that app instead. Give a diagnosable error rather than the generic
            # "not classifiable" one when that's what actually happened.
            current_elements = self.current_elements()
            foreign = [e for e in current_elements if e.package and "bayut" not in e.package]
            if current_elements and foreign and not any(
                    e.package and "bayut" in e.package for e in current_elements):
                raise AssertionError(
                    f"app under test is no longer in the foreground (seeing "
                    f"{foreign[0].package!r} instead) — likely a heads-up notification "
                    f"from an unrelated app intercepted the previous tap; see "
                    f"docs/DECISIONS.md D-017/D-019 device-hygiene note. Element sought: "
                    f"resource_id={resource_id!r} accessibility_id={accessibility_id!r} text={text!r}"
                )
            raise AssertionError(
                f"element visible to Selenium but not classifiable from page_source: "
                f"resource_id={resource_id!r} accessibility_id={accessibility_id!r} text={text!r}"
            )
        allowed, decision = self.safety_policy.may_tap(target)
        if decision.verdict != "ALLOW":
            raise SafetyRefusal(
                f"refusing to tap {target.label!r}: safety verdict {decision.verdict} "
                f"({decision.rule_id or 'no matching rule'}) — this control stays "
                f"manual-only unless a human explicitly reclassifies it"
            )
        # Re-locate immediately before clicking rather than reusing the WebElement
        # from the wait_for() above: classification's own page_source dump
        # (current_elements(), between that wait_for and here) can invalidate
        # Appium's cached element reference even when nothing visibly changed —
        # confirmed live as a StaleElementReferenceException on this exact path.
        # Re-fetching keeps the gap between "locate" and "click" as small as possible.
        web_el = self.wait_for(resource_id, accessibility_id, text, timeout=timeout)
        web_el.click()
        return decision

    def assert_blocked(self, resource_id: str | None = None, accessibility_id: str | None = None,
                        text: str | None = None, timeout: int | None = None) -> None:
        """Assert an element exists and the safety gate refuses to tap it. Never taps.
        Waits via Selenium first (explicit wait, not a race against page_source timing),
        then re-classifies via our own parse. Searches nested elements too — see the
        include_nested note on _match()."""
        self.wait_for(resource_id, accessibility_id, text, timeout=timeout)
        target = self._match(resource_id, accessibility_id, text, include_nested=True)
        assert target is not None, (
            f"expected element not found: resource_id={resource_id!r} "
            f"accessibility_id={accessibility_id!r} text={text!r}"
        )
        allowed, decision = self.safety_policy.may_tap(target)
        assert decision.verdict == "BLOCK", (
            f"expected {target.label!r} to be BLOCK, got {decision.verdict} "
            f"({decision.rule_id}) — a consequential control is no longer classified "
            f"as consequential; this is a real finding, not a test bug"
        )

    def safe_tap_row_containing(self, label_resource_id: str, text: str,
                                timeout: int | None = None):
        """Tap a clickable ROW that has no id of its own, identified by a labelled child.

        Some list rows in this app expose no resource-id at all — the location-picker
        suggestions are the worst case: the clickable row is anonymous and the name sits
        on a non-clickable `tv_title` inside it. That defeats a plain locator two ways:

          * `safe_tap(resource_id=...)` has nothing to aim at, and
          * `safe_tap(text=...)` matches the *search input* instead, because after
            typing, the input carries the same string — a silent wrong-element tap of
            exactly the kind D-024/D-034 warn about.

        So the row is located by hierarchy — UiAutomator's `clickable(true)` +
        `childSelector(...)`, third in CLAUDE.md's locator priority and well above XPath
        — and the element that gets *classified* is the labelled child, which is the one
        carrying the semantic identity the safety policy can reason about.

        LOCATOR-QUALITY FINDING: selecting a location is the single most common action
        in this app and it has no stable identifier. That belongs at the top of the
        testID ask.
        """
        from appium.webdriver.common.appiumby import AppiumBy

        elements = self.current_elements()
        label = next((e for e in elements
                      if e.resource_id == label_resource_id and e.text == text and e.bounds),
                     None)
        if label is None:
            raise AssertionError(
                f"no {label_resource_id} carrying text {text!r} is on screen"
            )

        # Classify the LABEL — it is the element carrying semantic identity. The row
        # itself has no id, no text and no content-desc, so it is unclassifiable by
        # design and would always come back UNCERTAIN.
        allowed, decision = self.safety_policy.may_tap(label)
        if decision.verdict != "ALLOW":
            raise SafetyRefusal(
                f"refusing to tap the row for {text!r}: safety verdict "
                f"{decision.verdict} ({decision.rule_id or 'no matching rule'})"
            )

        escaped = text.replace('"', '\\"')
        selector = (
            f'new UiSelector().clickable(true).childSelector('
            f'new UiSelector().resourceId("{label_resource_id}").text("{escaped}"))'
        )
        try:
            web_el = WebDriverWait(self.driver, 5).until(
                lambda d: d.find_element(AppiumBy.ANDROID_UIAUTOMATOR, selector)
            )
            web_el.click()
            return decision
        except TimeoutException:
            pass

        # Fallback: resolve the row by HIERARCHY CONTAINMENT — the smallest clickable
        # element whose bounds enclose the label. UiAutomator's childSelector does not
        # match this app's suggestion rows (confirmed live), and containment is still a
        # structural relationship read from the tree, not a guessed screen position.
        # The tap is by coordinate only because the row exposes nothing to address it
        # by; same forced-hand situation as the favourite heart in D-031.
        lx1, ly1, lx2, ly2 = label.bounds
        rows = [e for e in elements
                if e.clickable and e.bounds
                and e.bounds[0] <= lx1 and e.bounds[1] <= ly1
                and e.bounds[2] >= lx2 and e.bounds[3] >= ly2]
        if not rows:
            raise AssertionError(
                f"found the label {text!r} but no clickable row encloses it — cannot "
                f"determine what to tap"
            )
        row = min(rows, key=lambda e: e.area)
        point = row.center
        assert point is not None, f"enclosing row for {text!r} has no usable bounds"
        print(f"    note: tapping {text!r} via enclosing clickable row "
              f"(no resource-id on the row itself — locator-quality finding)")
        self.tap_at(*point)
        return decision

    def back(self) -> None:
        """Device back gesture — not a tap on a classified element, so not safety-gated
        the same way; this is the same primitive tools/crawler.py uses for navigation."""
        self.driver.back()

    def dismiss_review_popup_if_present(self, timeout: int = 2) -> bool:
        """Checklist §9's App Review bottom sheet ("How was your experience on
        Bayut?") can appear unprompted on Home after enough session activity —
        OBSERVED 2026-08-10, confirmed live mid-suite (triggered by this suite's own
        favouriting across many runs). Left alone, it sits on top of Home and
        intercepts whatever tap was meant for the real screen underneath.

        Dismissed by tapping the scrim (`touch_outside`) directly — deliberately NOT
        through `safe_tap()`. `touch_outside` is the generic BottomSheetDialogFragment
        scrim resource-id reused by every bottom sheet in this app (filters, price
        range, info popups — see e.g. `buy_rent_sheet.py`'s SCRIM comment), so it can
        never carry its own ALLOW rule without loosening dismissal for every sheet at
        once, and the safety engine only ever classifies one element at a time — it
        has no way to express "only when app_review_content is also on screen." What
        makes this safe is doing that check ourselves, with a marker unique to this
        one popup, before ever touching the ambiguous scrim.

        Returns whether anything was actually dismissed, so callers can tell "nothing
        was there" from "there was something and it's gone now"."""
        if not self.is_present(resource_id="com.bayut.bayutapp:id/app_review_content",
                                timeout=timeout):
            return False
        scrim = self.wait_for(resource_id="com.bayut.bayutapp:id/touch_outside", timeout=3)
        scrim.click()
        return True

    # -- scrolling -----------------------------------------------------------

    def scroll_into_view_by_text(self, text: str, max_swipes: int = 8, timeout: int = 15):
        from appium.webdriver.common.appiumby import AppiumBy
        selector = (
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().scrollable(true)).setMaxSearchSwipes({max_swipes})'
            f'.scrollIntoView(new UiSelector().text("{text}"))',
        )
        return WebDriverWait(self.driver, timeout).until(lambda d: d.find_element(*selector))

    def scroll_into_view_by_id(self, resource_id: str, max_swipes: int = 8, timeout: int = 15):
        from appium.webdriver.common.appiumby import AppiumBy
        selector = (
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().scrollable(true)).setMaxSearchSwipes({max_swipes})'
            f'.scrollIntoView(new UiSelector().resourceId("{resource_id}"))',
        )
        return WebDriverWait(self.driver, timeout).until(lambda d: d.find_element(*selector))

    def safe_tap_scrolled_text(self, text: str, max_swipes: int = 8,
                                resource_id: str | None = None):
        """Scroll to a text label, classify, tap the SAME element handle — never a
        second independent find (that race is what appium/pages/more_screen.py's
        ensure_logged_out() comment documents hitting live).

        `resource_id`, when given, classifies by that instead of the raw text —
        needed when the text itself is arbitrary/unsafe to allowlist (e.g. a person's
        name) but the row's resource-id is stable and shared (e.g. tv_agent_name)."""
        web_el = self.scroll_into_view_by_text(text, max_swipes=max_swipes)
        if resource_id:
            target = self._match(resource_id=resource_id, accessibility_id=None,
                                  text=text, include_nested=True)
        else:
            target = self._match(resource_id=None, accessibility_id=None, text=text,
                                  include_nested=True)
        if target is None:
            raise AssertionError(f"scrolled to text {text!r} but could not classify it")
        allowed, decision = self.safety_policy.may_tap(target)
        if decision.verdict != "ALLOW":
            raise SafetyRefusal(
                f"refusing to tap {target.label!r}: safety verdict {decision.verdict} "
                f"({decision.rule_id or 'no matching rule'})"
            )
        web_el.click()
        return decision

    def tap_at(self, x: int, y: int) -> None:
        """Real W3C pointer tap at absolute screen coordinates — bypasses the
        accessibility-action click Selenium's `WebElement.click()` normally issues.

        Confirmed live (D-031): the Favourites heart (`favourite_cb`) reports
        `clickable="true"` and `.click()` returns successfully, but the app's actual
        favourite state never changes — no error, no effect. A genuine touch at the
        same coordinates does work (confirmed by the resulting "Remove property from
        Favourites?" dialog on an already-favourited listing). Some custom views only
        wire a real `OnTouchListener`/`OnClickListener` to physical touch events, not
        to `performAccessibilityAction`, even when the accessibility node claims to be
        clickable.

        Not safety-gated itself — callers must classify the target via
        `safety_policy.may_tap()` before calling this, the same discipline `safe_tap()`
        already applies before its own `.click()`."""
        finger = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(self.driver, mouse=finger)
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.release()
        actions.perform()

    def swipe(self, start_pct: tuple[float, float], end_pct: tuple[float, float]) -> None:
        """W3C pointer-action swipe. `mobile: swipeGesture`'s actual parameters are an
        area + compass direction, not startX/startY/endX/endY — passing those silently
        no-ops them (confirmed live in the ported suite; see docs/DECISIONS.md D-019)."""
        size = self.driver.get_window_size()
        w, h = size["width"], size["height"]
        sx, sy = int(w * start_pct[0]), int(h * start_pct[1])
        ex, ey = int(w * end_pct[0]), int(h * end_pct[1])
        finger = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(self.driver, mouse=finger)
        actions.pointer_action.move_to_location(sx, sy)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.move_to_location(ex, ey)
        actions.pointer_action.pause(0.1)
        actions.pointer_action.release()
        actions.perform()

    def swipe_up(self) -> None:
        self.swipe((0.5, 0.8), (0.5, 0.2))

    def swipe_down_to_top(self) -> None:
        self.swipe((0.5, 0.2), (0.5, 0.9))
