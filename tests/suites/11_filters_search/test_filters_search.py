"""§11 Filters & search — docs/REGRESSION-CHECKLIST.md.

Covers: the full Filters sheet, and each quick-filter chip's own bottom sheet (Buy/Rent,
Property Types, Rental Frequency, Bedrooms, Price Range), plus the TruCheck toggle and
info popup. This is structural coverage — each sheet opens, shows its expected controls,
and can be dismissed cleanly. It does **not** verify filter *behaviour* (AND vs OR,
result-count deltas, boundary inclusivity) — that's PROBE mode's job
(`.claude/agents/app-cartographer.md` MODE 2), not a structural crawl, and hasn't been
run yet. The checklist's "Beds/Baths shouldn't appear for Commercial" note is exactly
that kind of behavioural check and is out of scope here.
"""
from __future__ import annotations


def test_full_filters_sheet_opens_and_closes(properties_screen):
    sheet = properties_screen.open_full_filters()
    try:
        assert sheet.is_displayed()
        assert sheet.is_present(resource_id=sheet.RESIDENTIAL_TYPE)
        assert sheet.is_present(resource_id=sheet.COMMERCIAL_TYPE)
        assert sheet.is_present(resource_id=sheet.RESET)
        assert "propert" in sheet.show_results_label().lower()
    finally:
        results = sheet.close()
        assert results.is_displayed()


def test_buy_rent_picker(properties_screen):
    sheet = properties_screen.open_buy_rent_picker()
    try:
        assert sheet.is_displayed()
        assert sheet.is_present(resource_id=sheet.BUY)
        assert sheet.is_present(resource_id=sheet.RENT)
    finally:
        results = sheet.dismiss()
        assert results.is_displayed()


def test_property_type_picker(properties_screen):
    sheet = properties_screen.open_property_type_picker()
    try:
        assert sheet.is_displayed()
        assert sheet.is_present(resource_id=sheet.RESIDENTIAL)
        assert sheet.is_present(resource_id=sheet.COMMERCIAL)
    finally:
        results = sheet.apply()
        assert results.is_displayed()


def test_rental_frequency_picker(properties_screen):
    sheet = properties_screen.open_rental_frequency_picker()
    try:
        assert sheet.is_displayed()
        for option_text in sheet.OPTIONS:
            assert sheet.option_present(sheet.OPTION, option_text), (
                f"expected Rental Frequency option {option_text!r} not found"
            )
    finally:
        results = sheet.apply()
        assert results.is_displayed()


def test_bedrooms_picker(properties_screen):
    sheet = properties_screen.open_bedrooms_picker()
    try:
        assert sheet.is_displayed()
        for option_text in sheet.OPTIONS:
            assert sheet.option_present(sheet.OPTION, option_text), (
                f"expected Bedrooms option {option_text!r} not found"
            )
    finally:
        results = sheet.apply()
        assert results.is_displayed()


def test_price_range_picker(properties_screen):
    sheet = properties_screen.open_price_range_picker()
    try:
        assert sheet.is_displayed()
        assert sheet.is_present(resource_id=sheet.MIN_INPUT)
        assert sheet.is_present(resource_id=sheet.MAX_INPUT)
    finally:
        results = sheet.apply()
        assert results.is_displayed()


def test_trucheck_switch_present(properties_screen):
    assert properties_screen.is_present(resource_id=properties_screen.TRUCHECK_SWITCH)


def test_trucheck_info_popup(properties_screen):
    popup = properties_screen.open_trucheck_info()
    assert popup.is_displayed()
    results = popup.dismiss()
    assert results.is_displayed()


def test_furnishing_status_options_present(properties_screen):
    assert properties_screen.is_present(resource_id=properties_screen.FURNISHING_ALL)
    assert properties_screen.is_present(resource_id=properties_screen.FURNISHING_FURNISHED)
    assert properties_screen.is_present(resource_id=properties_screen.FURNISHING_UNFURNISHED)
