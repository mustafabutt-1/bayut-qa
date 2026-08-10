"""Pytest fixtures for the Bayut Android suite.

Every fixture here follows the same rules as `tools/crawler.py`, because they drive the
same live, production app with a real test account:

  * No `pm clear` outside a deliberate first-run bootstrap. Bayut's onboarding is
    one-time and gated on app data, not process state — see D-015/D-016/D-018 in
    `docs/DECISIONS.md`. `no_reset=True` here assumes onboarding was already completed
    by hand once on this device (the same precondition the crawl needed).
  * No `sleep()` as a synchronization mechanism. `screen_objects/base.py` uses Selenium's
    `WebDriverWait` exclusively.
  * Every tap goes through `crawl_safety.SafetyPolicy` — see `BaseScreen.safe_tap()`.
    There is no second tap path, matching the non-negotiable rule in `CLAUDE.md`.
  * Nothing here invents a value. A missing required `.env` entry fails loudly at
    fixture setup, not with a confusing error three layers down.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(TESTS_DIR))

load_dotenv(REPO_ROOT / ".env")

from crawl_safety import SafetyPolicy  # noqa: E402


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in — see "
            f"docs/SETUP.md. Tests never invent a package name, host, or credential."
        )
    return value


@pytest.fixture(scope="session")
def app_package() -> str:
    return _require_env("BAYUT_APP_PACKAGE")


@pytest.fixture(scope="session")
def safety_policy(app_package: str) -> SafetyPolicy:
    """The one and only tap gate. Identical policy the live crawl used."""
    config = REPO_ROOT / "context" / "crawl-allowlist.yaml"
    return SafetyPolicy.load(str(config) if config.exists() else None, app_package=app_package)


@pytest.fixture(scope="session")
def driver(app_package: str):
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    from adb import Adb, AdbError

    # DEVICE_D1_SERIAL is an optional override now, not a required manual edit —
    # Adb.require_device() auto-picks the one connected device (the common case) and
    # only needs a serial to disambiguate when several are attached at once. See
    # docs/DECISIONS.md D-030.
    adb_path = os.environ.get("ADB_PATH")
    configured_serial = os.environ.get("DEVICE_D1_SERIAL") or None
    try:
        device = Adb(serial=configured_serial, adb_path=adb_path).require_device()
    except AdbError as exc:
        raise RuntimeError(
            f"{exc}\n\nDEVICE_D1_SERIAL in .env is only needed to pick one device out "
            f"of several connected at once — leave it blank for a single device."
        ) from exc

    # Build-drift guard — OBSERVED 2026-08-10: a connected device running a different
    # app build than the one locators were captured against produces a wall of
    # scattered "element not found" failures that look exactly like device-portability
    # bugs, and cost real time to correctly diagnose as build drift instead. Surface
    # the mismatch up front rather than letting it masquerade as broken tests.
    expected_build = os.environ.get("BAYUT_BUILD_VERSION", "").strip()
    if expected_build:
        try:
            installed_version = Adb(serial=device.serial, adb_path=adb_path) \
                .app_version(app_package)["version_name"]
        except AdbError:
            installed_version = ""
        if installed_version and installed_version not in expected_build:
            print(
                f"\n*** BUILD MISMATCH: .env expects {expected_build!r}, device "
                f"{device.serial} has {installed_version!r} installed. Locator "
                f"failures below may be build drift, not real bugs — see "
                f"docs/DECISIONS.md D-030. ***\n"
            )

    opts = UiAutomator2Options()
    opts.platform_name = "Android"
    opts.automation_name = os.environ.get("APPIUM_AUTOMATION_NAME", "UiAutomator2")
    opts.app_package = app_package
    activity = os.environ.get("BAYUT_APP_ACTIVITY")
    if activity:
        opts.app_activity = activity
    opts.udid = device.serial
    # Never wipe app data from a test run. See module docstring.
    opts.no_reset = True
    opts.new_command_timeout = int(os.environ.get("APPIUM_NEW_COMMAND_TIMEOUT", "120"))
    opts.auto_grant_permissions = False  # permissions are a test surface, never silent
    server = os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723")

    drv = webdriver.Remote(server, options=opts)
    drv.update_settings({"waitForIdleTimeout": 0})
    yield drv
    drv.quit()


@pytest.fixture
def explicit_wait_seconds() -> int:
    return int(os.environ.get("DEFAULT_EXPLICIT_WAIT", "15"))


@pytest.fixture
def home_screen(driver, safety_policy):
    """Bottom-nav Home. `activate_app` only foregrounds the app — it resumes wherever
    the app process last was, it does not navigate to Home. Several screens (Activity
    Log, Favourites, Agent/Agency detail) are nested full-screen activities with no
    bottom nav at all, so a single "tap Home" fallback isn't enough from there —
    confirmed live, this is exactly the same device behaviour the ported suite's
    `_reset_to_home()`/`relaunch()` were built around (docs/DECISIONS.md D-019). Press
    back repeatedly until the Home tab's own marker is visible, then tap Home."""
    from selenium.common.exceptions import TimeoutException

    from screen_objects.base import BaseScreen
    from screen_objects.home_screen import HomeScreen

    driver.activate_app(_require_env("BAYUT_APP_PACKAGE"))
    screen = HomeScreen(driver, safety_policy)
    nav = BaseScreen(driver, safety_policy)

    for _ in range(8):
        if screen.is_displayed(timeout=1):
            break
        try:
            nav.safe_tap(accessibility_id="Home", timeout=2)
            break
        except (TimeoutException, AssertionError):
            driver.back()

    assert screen.is_displayed(timeout=5), (
        "Home screen not displayed even after backing out repeatedly — is the device "
        "sitting on an unexpected screen (a leftover dialog, a different app)? See "
        "docs/PROMPTS.md P3 for the manual recovery steps this session needed."
    )
    # §9's App Review bottom sheet ("How was your experience on Bayut?") can appear
    # unprompted right here — this is its own documented trigger point. Left alone it
    # would intercept the next test's first tap. See dismiss_review_popup_if_present()
    # in screen_objects/base.py and docs/DECISIONS.md D-028.
    screen.dismiss_review_popup_if_present()
    return screen


@pytest.fixture
def properties_screen(home_screen):
    """Properties results (LPV) — the shared starting point for most suites below.
    Idempotent: tapping the bottom-nav Properties icon is harmless if already there."""
    return home_screen.open_properties()
