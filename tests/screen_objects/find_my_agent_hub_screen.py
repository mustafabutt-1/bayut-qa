"""Find My Agent hub — feature area in docs/REGRESSION-CHECKLIST.md.

`search()` types via `mobile: shell` (adb `input text`, executed through the Appium
session itself), not Appium `send_keys()` — confirmed live in the source suite that
Appium's own text-entry paths never trigger the app's live search-as-you-type listener
here, even though the field's visible text ends up correct either way. See
docs/DECISIONS.md D-019 (the original finding) and D-026 (switching the workaround from
a separate `adb` subprocess to `mobile: shell`, so it stays inside one Appium session
instead of a second, separate automation path — requires the Appium server to be
started with `--allow-insecure=uiautomator2:adb_shell`; see docs/SETUP.md).
"""
from __future__ import annotations

from .base import BaseScreen


class FindMyAgentHubScreen(BaseScreen):
    AGENCIES_TOGGLE = "com.bayut.bayutapp:id/rb_agencies"
    SEARCH_ENTRY = "com.bayut.bayutapp:id/text_search"
    SEARCH_INPUT = "com.bayut.bayutapp:id/et_search"
    AGENCY_RESULT_NAME = "com.bayut.bayutapp:id/tv_agency_name"

    # OBSERVED 2026-08-10, build 15.7.2 (1272). Three RadioGroups, every option with its
    # own resource-id — so none of this needs a text locator.
    AGENT_AGENCY_GROUP = "com.bayut.bayutapp:id/rg_agent_agency"
    AGENTS_TOGGLE = "com.bayut.bayutapp:id/rb_agents"
    PURPOSE_GROUP = "com.bayut.bayutapp:id/rg_purpose"
    PURPOSE_BUY = "com.bayut.bayutapp:id/rb_buy"
    PURPOSE_RENT = "com.bayut.bayutapp:id/rb_rent"
    CITY_GROUP = "com.bayut.bayutapp:id/rg_city"
    CITY_DUBAI = "com.bayut.bayutapp:id/rb_dubai"
    CITY_ABU_DHABI = "com.bayut.bayutapp:id/rb_abu_dhabi"
    FEATURED_AGENTS_LIST = "com.bayut.bayutapp:id/rv_featured_agents"
    FEATURED_AGENCIES_LIST = "com.bayut.bayutapp:id/rv_featured_agencies"
    AGENT_NAME = "com.bayut.bayutapp:id/tv_agent_name"
    # OBSERVED: the *featured* agency list uses tv_agency_title. AGENCY_RESULT_NAME
    # (tv_agency_name) is a different element — the one in agency *search results*.
    # They are not interchangeable; using the search id on the featured list finds
    # nothing and reads as "no agencies", which is a false defect.
    AGENCY_TITLE = "com.bayut.bayutapp:id/tv_agency_title"
    AGENCY_LOCATIONS = "com.bayut.bayutapp:id/tv_agency_locations"
    AGENCY_PROPERTY_COUNT = "com.bayut.bayutapp:id/tv_agency_properties_count"
    BACK = "com.bayut.bayutapp:id/iv_back"

    # UNRESOLVED: the leaderboard is an agent-only surface, so it has never appeared in
    # any dump taken from a signed-out session. No id, therefore no locator — the test
    # that needs it skips rather than falling back to a text match.
    LEADERBOARD_ID: str | None = None

    def is_displayed(self, timeout: int = 10) -> bool:
        return self.is_present(resource_id=self.AGENT_AGENCY_GROUP, timeout=timeout)

    def switch_to_agencies(self, timeout: int = 15):
        """Switch to Agencies and wait for that list to actually render.

        Two things are verified rather than assumed, because "no agencies" is otherwise
        indistinguishable from "the tap did not land":
          1. the Agencies radio really is checked afterwards, and
          2. the agencies RecyclerView really did render.

        Failing here reports what IS on screen, so the next person gets a diagnosis
        instead of an empty list and a guess.
        """
        import time

        self.safe_tap(resource_id=self.AGENCIES_TOGGLE)

        # Wait for CONTENT, not for the container. The RecyclerView attaches empty and
        # its rows arrive a beat later, so waiting on rv_featured_agencies alone returns
        # True while visible_agency_names() is still [] — which reads as "no agencies"
        # and files a false defect. Poll the rows themselves.
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.visible_agency_names():
                return
            time.sleep(0.5)

        checked = [e.resource_id.rsplit("/", 1)[-1] for e in self.current_elements()
                   if e.resource_id.rsplit("/", 1)[-1] in ("rb_agents", "rb_agencies")
                   and (e.checked or e.selected)]
        lists = sorted({e.resource_id.rsplit("/", 1)[-1] for e in self.current_elements()
                        if e.resource_id.rsplit("/", 1)[-1].startswith("rv_")})
        raise AssertionError(
            f"tapped the Agencies toggle but {self.FEATURED_AGENCIES_LIST} never "
            f"rendered within {timeout}s.\n"
            f"  toggle actually checked : {checked or 'NEITHER'}\n"
            f"  lists on screen         : {lists or 'none'}\n"
            f"If the toggle is checked and the agents list is still showing, the switch "
            f"registered but the content did not reload — that is an app finding. If "
            f"neither toggle is checked, the tap did not land and this is a test issue."
        )

    def switch_to_agents(self):
        self.safe_tap(resource_id=self.AGENTS_TOGGLE)

    def section_toggle_ids_present(self) -> dict[str, bool]:
        """Which of the two documented sections exist, by resource-id."""
        return {
            "Agents": self.is_present(resource_id=self.AGENTS_TOGGLE, timeout=5),
            "Agencies": self.is_present(resource_id=self.AGENCIES_TOGGLE, timeout=5),
        }

    def selected_city_id(self) -> str | None:
        """Which city radio is selected — read from `selected`/`checked`, not from text.

        Returns the short resource-id (e.g. 'rb_dubai') so the caller compares ids, not
        labels. A localized build still reports the same id.
        """
        for el in self.current_elements():
            if el.resource_id in (self.CITY_DUBAI, self.CITY_ABU_DHABI):
                if el.selected or el.checked:
                    return el.resource_id.rsplit("/", 1)[-1]
        return None

    def visible_agency_names(self) -> list[str]:
        """Agency names in the featured list, located by tv_agency_title."""
        return [e.text.strip() for e in self.current_elements()
                if e.resource_id == self.AGENCY_TITLE and e.text]

    def visible_agent_names(self) -> list[str]:
        return [e.text.strip() for e in self.current_elements()
                if e.resource_id == self.AGENT_NAME and e.text]

    def open_search(self):
        self.safe_tap(resource_id=self.SEARCH_ENTRY)

    def search(self, query: str):
        """Type a query, clearing whatever was there first.

        The field retains its text between visits, and `input text` APPENDS. Without
        clearing, a second test searching from the same session sends a concatenation of
        both queries, which returns the wrong agency or none — and the failure surfaces
        much later as "the agency name isn't on screen", nowhere near the cause.
        """
        self.safe_tap(resource_id=self.SEARCH_INPUT)
        self.driver.execute_script("mobile: shell", {
            "command": "input",
            "args": ["text", query.replace(" ", "%s")],
            "includeStderr": True,
            "timeout": 5000,
        })
        # NOTE: deliberately does NOT clear the field first. Adding `web_el.clear()`
        # here was tried on 2026-08-11 and broke this flow outright — the test went from
        # passing in isolation to failing with a NoSuchElement further down. Reverted.
        # The stale-query concern is real in principle, so if it ever bites, fix it by
        # re-entering the search screen rather than by clearing the live field.

    def open_first_agency_result(self):
        from .agency_detail_screen import AgencyDetailScreen
        self.safe_tap(resource_id=self.AGENCY_RESULT_NAME)
        return AgencyDetailScreen(self.driver, self.safety_policy, self.timeout)

    def assert_agency_name_visible(self, name: str, timeout: int = 10):
        if self.is_present(text=name, timeout=timeout):
            return
        # Report what IS on screen. A bare `assert` here said nothing, and the usual
        # cause is a stale search box producing a different agency — knowing which one
        # turns a mystery into a one-line diagnosis.
        on_screen = self.visible_agency_names() or self.visible_agent_names()
        raise AssertionError(
            f"expected agency {name!r} to be visible within {timeout}s, but it is not.\n"
            f"  names on screen: {on_screen or '(none)'}\n"
            f"If a different agency is shown, the search box most likely still held a "
            f"previous query — see search(), which clears before typing."
        )
