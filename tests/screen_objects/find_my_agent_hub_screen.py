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

    def switch_to_agencies(self):
        self.safe_tap(resource_id=self.AGENCIES_TOGGLE)

    def open_search(self):
        self.safe_tap(resource_id=self.SEARCH_ENTRY)

    def search(self, query: str):
        self.safe_tap(resource_id=self.SEARCH_INPUT)
        self.driver.execute_script("mobile: shell", {
            "command": "input",
            "args": ["text", query.replace(" ", "%s")],
            "includeStderr": True,
            "timeout": 5000,
        })

    def open_first_agency_result(self):
        from .agency_detail_screen import AgencyDetailScreen
        self.safe_tap(resource_id=self.AGENCY_RESULT_NAME)
        return AgencyDetailScreen(self.driver, self.safety_policy, self.timeout)

    def assert_agency_name_visible(self, name: str, timeout: int = 10):
        assert self.is_present(text=name, timeout=timeout)
