"""Properties results (LPV) — OBSERVED 2026-08-10, build 15.7.2 (1272), en-GB.

Fingerprint `12a43c89364e` / `99a92dbe3684` (same screen; fingerprint shifts slightly
with live result-set content, per D-012's structural-fingerprint design).
"""
from __future__ import annotations

from selenium.common.exceptions import TimeoutException

from .base import BaseScreen, SafetyRefusal, tappable


class PropertiesResultsScreen(BaseScreen):
    SELECT_LOCATION = "com.bayut.bayutapp:id/tv_selected_locations"
    SAVE_SEARCH = "com.bayut.bayutapp:id/save_text_tb_rev_1"        # BLOCK-BAYUT-SAVE-SEARCH
    QUICK_FILTER = "com.bayut.bayutapp:id/tv_quick_filter"          # icon + Rent/Residential/Yearly/Beds/Price chips, disambiguate by text
    TRUCHECK_ICON = "com.bayut.bayutapp:id/trucheck_icon"           # opens info popup
    TRUCHECK_SWITCH = "com.bayut.bayutapp:id/trucheck_switch"
    FURNISHING_ALL = "com.bayut.bayutapp:id/rb_all_furnishing_status"
    FURNISHING_FURNISHED = "com.bayut.bayutapp:id/rb_furnished"
    FURNISHING_UNFURNISHED = "com.bayut.bayutapp:id/rb_unfurnished"
    LISTING_CARD = "com.bayut.bayutapp:id/item_card_listing"
    FAB_MAP = "com.bayut.bayutapp:id/fab_map"
    FAB_SORT = "com.bayut.bayutapp:id/fab_sort"

    # Lead controls, present directly on each listing fat card — must stay BLOCK.
    LEAD_EMAIL = "com.bayut.bayutapp:id/btn_email"
    LEAD_CALL = "com.bayut.bayutapp:id/btn_call"
    LEAD_WHATSAPP = "com.bayut.bayutapp:id/btn_whatsapp"
    FAVOURITE_CHECKBOX = "com.bayut.bayutapp:id/favourite_cb"

    # --- §16 LPV inline widgets -------------------------------------------
    # Matched on visible text / content-desc / resource-id, NOT on a known widget id:
    # the crawl's page-source dumps are gitignored, so the container ids for these
    # widgets have never been observed here. Text matching is locale-fragile — these
    # only hold in English. Replace each with its resource-id after the first live run
    # prints them (see test_inline_widgets.py, which reports what it actually matched).
    # [UNVERIFIED — replace with resource-ids]
    INLINE_WIDGET_MARKERS: dict[str, str] = {
        "TruBroker": r"tru\s*broker",
        "BayutGPT": r"bayut\s*gpt",
        "TruEstimate": r"tru\s*estimate",
        "Dubai Transactions": r"dubai\s*transaction",
        "Alert Me of New Properties": r"alert\s*me\s*of\s*new",
        "Off-Plan rail": r"off[\s\-_]?plan",
    }

    # Checklist §16: documented positions, i.e. the widget appears after the Nth
    # listing. Used for relative-order assertions, not absolute indexing — see
    # observed_widget_order().
    DOCUMENTED_WIDGET_ORDER: tuple[str, ...] = (
        "TruBroker",            # after listing 1
        "BayutGPT",             # after listing 3
        "TruEstimate",          # after listing 7
        "Dubai Transactions",   # after listing 10
    )

    def observed_widget_order(self, max_swipes: int = 12) -> list[tuple[str, int]]:
        """Scroll the LPV and record inline widgets in the order they appear.

        Returns ``[(widget_name, listing_cards_seen_before_it), ...]``.

        The card count is **best-effort evidence, not an assertion target**. Counting
        absolute position across scrolls means de-duplicating cards that reappear
        between screenfuls, and two listings in the same tower can share a price, so
        the count can drift. Relative order cannot drift that way, which is why the
        test asserts order and merely reports the counts.

        The checklist is explicit that "only inline filters containing data will be
        visible", so a widget being absent is NOT a defect and this returns whatever
        it finds.
        """
        import re

        self.swipe_down_to_top()
        found: list[tuple[str, int]] = []
        seen_names: set[str] = set()
        card_keys: list[str] = []

        for _ in range(max_swipes):
            elements = sorted(
                (e for e in self.current_elements() if e.bounds),
                key=lambda e: e.bounds[1],
            )
            for el in elements:
                haystack = f"{el.text or ''} {el.content_desc or ''} {el.resource_id or ''}"
                if el.resource_id == self.LISTING_CARD:
                    key = f"{el.bounds[1]}:{(el.text or '')[:24]}"
                    if key not in card_keys:
                        card_keys.append(key)
                    continue
                for name, pattern in self.INLINE_WIDGET_MARKERS.items():
                    if name in seen_names:
                        continue
                    if re.search(pattern, haystack, re.IGNORECASE):
                        seen_names.add(name)
                        found.append((name, len(card_keys)))
            if len(seen_names) == len(self.INLINE_WIDGET_MARKERS):
                break
            self.swipe_up()
        return found

    def is_displayed(self) -> bool:
        return self.is_present(resource_id=self.SELECT_LOCATION)

    def open_location_picker(self):
        from .location_picker_screen import LocationPickerScreen
        self.safe_tap(resource_id=self.SELECT_LOCATION)
        return LocationPickerScreen(self.driver, self.safety_policy, self.timeout)

    def open_full_filters(self):
        """The leading filter-icon quick-filter chip (empty text) opens the full sheet."""
        from .filters_sheet_screen import FiltersSheetScreen
        self.safe_tap(resource_id=self.QUICK_FILTER, text="")
        return FiltersSheetScreen(self.driver, self.safety_policy, self.timeout)

    def open_buy_rent_picker(self):
        from .buy_rent_sheet import BuyRentSheet
        self.safe_tap(resource_id=self.QUICK_FILTER, text="Rent")
        return BuyRentSheet(self.driver, self.safety_policy, self.timeout)

    def open_property_type_picker(self):
        from .property_type_sheet import PropertyTypeSheet
        self.safe_tap(resource_id=self.QUICK_FILTER, text="Residential")
        return PropertyTypeSheet(self.driver, self.safety_policy, self.timeout)

    def open_rental_frequency_picker(self):
        from .rental_frequency_sheet import RentalFrequencySheet
        self.safe_tap(resource_id=self.QUICK_FILTER, text="Yearly")
        return RentalFrequencySheet(self.driver, self.safety_policy, self.timeout)

    def open_bedrooms_picker(self):
        from .bedrooms_sheet import BedroomsSheet
        self.safe_tap(resource_id=self.QUICK_FILTER, text="Beds")
        return BedroomsSheet(self.driver, self.safety_policy, self.timeout)

    def open_price_range_picker(self):
        from .price_range_sheet import PriceRangeSheet
        self.safe_tap(resource_id=self.QUICK_FILTER, text="Price")
        return PriceRangeSheet(self.driver, self.safety_policy, self.timeout)

    def open_trucheck_info(self):
        from .info_popup_screen import InfoPopupScreen
        self.safe_tap(resource_id=self.TRUCHECK_ICON)
        return InfoPopupScreen(self.driver, self.safety_policy, self.timeout)

    def open_first_listing(self):
        from .listing_detail_screen import ListingDetailScreen
        self.safe_tap(resource_id=self.LISTING_CARD)
        return ListingDetailScreen(self.driver, self.safety_policy, self.timeout)

    PRICE_TV = "com.bayut.bayutapp:id/price_tv"

    def first_listing_price(self, timeout: int = 10) -> str | None:
        """§20 Favourites / DPV-marks-viewed cross-check: the price text is how the
        ported suite matches "the listing I just acted on" back up in Activity Log,
        since IDs aren't visible in the UI (context/listing-id-visibility.md).

        Waits for at least one price_tv first — the results list shows grey
        loading-skeleton placeholders immediately after navigating here (same
        skeleton-loading behaviour FavouritesScreen.wait_for_first_card() already
        documents), so an unwaited read can race the skeleton and come back empty."""
        try:
            self.wait_for(resource_id=self.PRICE_TV, timeout=timeout)
        except TimeoutException:
            return None
        els = [e for e in self.current_elements() if e.resource_id == self.PRICE_TV]
        return els[0].text if els else None

    def favourite_nth_listing(self, index: int = 0) -> str | None:
        """§20 Favourites — the heart/checkbox on a listing fat card. `favourite_cb`
        matches ALLOW-NAV-TABS ("favou?rites?"); classified through the gate like every
        other tap, one card among several sharing the resource-id, picked by index.

        Tapped via `tap_at()`, not `.click()` — confirmed live (D-031): this control
        reports `clickable="true"` but its `checked`/`selected` attributes never
        change and `.click()` silently has no effect on the app's real favourite
        state. A genuine coordinate touch does work.

        Idempotency can't be read from the checkbox's own attributes (they never
        reflect state — see above), so it's detected from a real behavioural signal
        instead: tapping an ALREADY-favourited listing triggers a "Remove property
        from Favourites?" confirmation (only on removal, never on addition). If that
        dialog appears, this method declines it (taps "No") and returns — the
        listing stays favourited exactly as it already was, which is what "ensure
        this is favourited" should do, not silently remove it.

        Returns the price of the listing acted on, read from the same page_source
        snapshot used to locate the checkbox — not a separate first_listing_price()
        call beforehand. Confirmed live: production's result order can shift between
        two page_source reads even a few seconds apart (D-007's "live inventory
        mutates" risk), so a caller reading the price first and favouriting by index
        second can end up cross-checking against a different listing than the one
        actually favourited."""
        elements = self.current_elements()
        candidates = [el for el in tappable(elements, include_nested=True)
                      if el.resource_id == self.FAVOURITE_CHECKBOX]
        assert len(candidates) > index, (
            f"expected at least {index + 1} favourite checkbox(es), found {len(candidates)}"
        )
        target = candidates[index]
        prices = [el for el in elements if el.resource_id == self.PRICE_TV]
        price = prices[index].text if len(prices) > index else None

        allowed, decision = self.safety_policy.may_tap(target)
        if decision.verdict != "ALLOW":
            raise SafetyRefusal(
                f"refusing to tap {target.label!r}: safety verdict {decision.verdict} "
                f"({decision.rule_id or 'no matching rule'})"
            )
        center = target.center
        assert center is not None, f"favourite checkbox at index {index} has no usable bounds"
        self.tap_at(*center)

        if self.is_present(text="Remove property from Favourites?", timeout=2):
            self.safe_tap(resource_id="com.bayut.bayutapp:id/btn_no")
        return price
