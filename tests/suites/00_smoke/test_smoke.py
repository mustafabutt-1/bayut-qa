"""Smoke — app launches, bottom nav visible. Ported 1:1 from appium/tests/test_smoke.py
(docs/DECISIONS.md D-019); ordered first since it's the cheapest possible signal that
the environment itself (device, Appium server, app installed) is working before
anything else runs."""
from __future__ import annotations


def test_app_launches_and_bottom_nav_visible(home_screen):
    assert home_screen.is_displayed()
