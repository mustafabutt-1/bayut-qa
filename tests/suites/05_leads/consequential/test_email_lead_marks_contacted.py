"""§5 Leads — email lead, end-to-end. CONSEQUENTIAL, opt-in only.

Ported from appium/tests/test_email_lead_marks_contacted.py (docs/DECISIONS.md D-019).
This is the one test in the whole suite that submits a real lead. It is safe to run
repeatedly because it targets the QA team's own sanctioned test agency/account
(docs/REGRESSION-CHECKLIST.md §5: "Test Agency to be used: Explorer Real Estate"),
not because the tap itself is exempted from the shared policy — `btn_email` is and
stays BLOCK-LEAD-EMAIL there. The two consequential taps here (open the email-lead
form, submit it) go through `deliberate_tap()`, which screenshots and logs before every
one of them (see tests/screen_objects/consequential.py) — the same evidence discipline
CLAUDE.md requires of every consequential action.

The agency name is verified via `assert_agency_name_visible` immediately after landing
on the agency's page — before switching tabs, before opening a listing, before either
consequential tap. That ordering is the safety property of this whole test: a mismatch
here fails loudly, before anything is submitted.

Requires RUN_CONSEQUENTIAL_TESTS=1 to run at all — a real environment check, not just a
folder/marker convention, so `pytest tests/` alone can never trigger this.
"""
from __future__ import annotations

import os

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait

from screen_objects.consequential import deliberate_tap

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CONSEQUENTIAL_TESTS") != "1",
    reason="Consequential test (submits a real lead, even if to a QA-sanctioned test "
           "agency). Set RUN_CONSEQUENTIAL_TESTS=1 to run deliberately.",
)

AGENCY = os.environ.get("TEST_LEAD_AGENCY_NAME", "")
LEAD_NAME = os.environ.get("TEST_LEAD_NAME", "")
LEAD_EMAIL = os.environ.get("TEST_LEAD_EMAIL", "")
LEAD_PHONE = os.environ.get("TEST_LEAD_PHONE", "")


def _find_text(driver, text, timeout=15):
    return WebDriverWait(driver, timeout).until(
        lambda d: d.find_element(AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{text}")')
    )


def _find_id(driver, resource_id, timeout=15):
    return WebDriverWait(driver, timeout).until(lambda d: d.find_element(AppiumBy.ID, resource_id))


def test_email_lead_marks_contacted(home_screen):
    assert AGENCY and LEAD_NAME and LEAD_EMAIL and LEAD_PHONE, (
        "TEST_LEAD_AGENCY_NAME / TEST_LEAD_NAME / TEST_LEAD_EMAIL / TEST_LEAD_PHONE "
        "must be set in .env"
    )
    driver = home_screen.driver

    more = home_screen.open_more()
    hub = more.open_find_my_agent()
    hub.switch_to_agencies()
    hub.open_search()
    hub.search(AGENCY)
    agency = hub.open_first_agency_result()

    # Safety property of this whole test: verified before anything consequential.
    hub.assert_agency_name_visible(AGENCY)

    agency.switch_to_properties_tab()
    agency.assert_properties_list_visible()

    listing_price = agency.first_property_price()
    agency.open_nth_property(0)

    dpv_back = _find_id(driver, "com.bayut.bayutapp:id/ib_back_button")  # confirms DPV loaded
    assert dpv_back.is_displayed()

    email_btn = _find_id(driver, "com.bayut.bayutapp:id/btn_email")
    deliberate_tap(driver, email_btn,
                    reason=f"open the email-lead form on a {AGENCY} listing (QA-sanctioned "
                           f"test agency, docs/REGRESSION-CHECKLIST.md §5)",
                    evidence_tag="email-lead-open-form")

    assert _find_text(driver, "Name*", timeout=10).is_displayed()
    assert _find_text(driver, "Email Address*", timeout=5).is_displayed()
    assert _find_text(driver, "Phone*", timeout=5).is_displayed()
    assert _find_text(driver, "Message*", timeout=5).is_displayed()

    _find_id(driver, "com.bayut.bayutapp:id/edt_name").send_keys(LEAD_NAME)
    _find_id(driver, "com.bayut.bayutapp:id/edt_email").send_keys(LEAD_EMAIL)
    _find_id(driver, "com.bayut.bayutapp:id/et_phone").send_keys(LEAD_PHONE)

    send_btn = _find_id(driver, "com.bayut.bayutapp:id/send_btn")
    deliberate_tap(driver, send_btn,
                    reason=f"submit the email lead to {AGENCY} ({LEAD_EMAIL}) — the actual "
                           f"consequential action this test exists to verify",
                    evidence_tag="email-lead-submit")

    # Form closed, back on DPV.
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    try:
        driver.find_element(AppiumBy.ID, "com.bayut.bayutapp:id/send_btn")
        assert False, "email-lead form still visible after submit"
    except (NoSuchElementException, TimeoutException):
        pass
    assert _find_id(driver, "com.bayut.bayutapp:id/tv_currency_price", timeout=10).is_displayed()

    driver.terminate_app(os.environ["BAYUT_APP_PACKAGE"])
    driver.activate_app(os.environ["BAYUT_APP_PACKAGE"])

    more2 = home_screen.open_more()
    activity_log = more2.open_activity_log()
    activity_log.open_contacted_tab()
    activity_log.assert_entry_visible(listing_price)
