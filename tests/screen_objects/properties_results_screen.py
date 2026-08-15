"""Properties results (LPV) — OBSERVED 2026-08-10, build 15.7.2 (1272), en-GB.

Fingerprint `12a43c89364e` / `99a92dbe3684` (same screen; fingerprint shifts slightly
with live result-set content, per D-012's structural-fingerprint design).
"""
from __future__ import annotations

from selenium.common.exceptions import TimeoutException

from .base import BaseScreen, tappable


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
    # Matched on **resource-id**, never on visible text: a text match would stop working
    # in ar/ru/zh, three of the app's four shipped locales.
    #
    # OBSERVED 2026-08-10, build 15.7.2 (1272), across 18 page-source dumps of a
    # scrolled LPV: only the TruBroker widget was ever present, as
    # `cl_trubroker_container`. The other four documented widgets never appeared, which
    # is consistent with §16 ("only inline filters containing data will be visible") and
    # with the location gating — the capture had no location applied.
    #
    # UNRESOLVED ids are deliberately left as None rather than guessed. A widget with no
    # id here is reported as un-checkable, not silently treated as absent.
    INLINE_WIDGET_IDS: dict[str, str | None] = {
        "TruBroker": "com.bayut.bayutapp:id/cl_trubroker_container",
        "BayutGPT": None,                    # UNRESOLVED — never observed
        "TruEstimate": None,                 # UNRESOLVED — never observed
        "Dubai Transactions": None,          # UNRESOLVED — never observed
        "Alert Me of New Properties": None,  # UNRESOLVED — never observed
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

    #: What tv_selected_locations reads when NO location is applied. English only —
    #: see ensure_default_location() for why that is safe here.
    NO_LOCATION_LABELS: tuple[str, ...] = ("Select location",)

    def ensure_default_location(self) -> bool:
        """Clear any applied location so the next test starts from a known search.

        The app persists the last search across screens and across tests. Until now
        every test was read-only navigation, so the suite got away with having no state
        isolation; the moment one test applied a location filter, seven unrelated tests
        failed — most visibly the one asserting the eight emirates appear under Popular
        Locations, because Popular shows *child locations of the applied location*
        (checklist §13), not the emirates.

        Returns True if it actually reset something, so callers can report it.

        Locale note: the clean-state check compares against an English placeholder. In
        another locale the label will not match and this resets every time — slower, but
        it fails **safe** (over-cleaning) rather than open (leaking state into the next
        test), which is the right direction for an isolation guard.
        """
        label = next((e for e in self.current_elements()
                      if e.resource_id == self.SELECT_LOCATION), None)
        if label is None:
            return False  # not on the LPV; nothing to reset
        if (label.text or "").strip() in self.NO_LOCATION_LABELS:
            return False  # already clean

        picker = self.open_location_picker()
        picker.safe_tap(resource_id=picker.RESET)
        filters = picker.confirm()
        if not self.is_present(resource_id=self.LISTING_CARD, timeout=5):
            filters.show_results()
        return True

    def search_locations(self, *names: str, reset_first: bool = True):
        """Apply an exact set of locations and land back on results.

        Resets by default: the picker accumulates, so without a reset a test that asks
        for one location can silently be running against three left over from the last
        one — which matters enormously for the TruBroker widget rules, where "multiple
        locations" is itself the condition under test.
        """
        picker = self.open_location_picker()
        if reset_first:
            picker.safe_tap(resource_id=picker.RESET)
        for name in names:
            picker.select_location(name)

        filters = picker.confirm()
        # "Done" lands somewhere that depends on where the picker was opened from.
        # Opened from the Filters sheet it returns there, and the results still need
        # "Show N properties". Opened from the results screen — this path — it goes
        # straight back to results, and waiting for that button times out on a screen
        # that will never show it. Decide from what is actually on screen rather than
        # assuming one route (OBSERVED 2026-08-11).
        if self.is_present(resource_id=self.LISTING_CARD, timeout=5):
            return self
        return filters.show_results()

    def has_inline_widget(self, name: str, max_swipes: int = 12) -> bool:
        """Is a named inline widget anywhere on this result set?"""
        return name in dict(self.observed_widget_order(max_swipes=max_swipes))

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
        known = {rid: name for name, rid in self.INLINE_WIDGET_IDS.items() if rid}
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
                if el.resource_id == self.LISTING_CARD:
                    key = f"{el.bounds[1]}:{(el.text or '')[:24]}"
                    if key not in card_keys:
                        card_keys.append(key)
                    continue
                name = known.get(el.resource_id)
                if name and name not in seen_names:
                    seen_names.add(name)
                    found.append((name, len(card_keys)))
            if len(seen_names) == len(known):
                break
            self.swipe_up()
        return found

    def unresolved_widget_names(self) -> list[str]:
        """Widgets the checklist documents but for which no resource-id is known.

        Reported by the tests so an absent widget is never confused with an
        un-checkable one.
        """
        return [n for n, rid in self.INLINE_WIDGET_IDS.items() if not rid]

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

    def locate_favourite_checkbox(self, index: int = 0) -> tuple[str | None, tuple[int, int]]:
        """§20 Favourites — locate the heart/checkbox on a listing fat card, one card
        among several sharing the resource-id, picked by index. Read-only: finds the
        element and returns its price and tap-point center, but never taps it.

        `favourite_cb` is `PROD-BLOCK-FAVOURITE` — favouriting writes real account
        data, so this deliberately does not call `safe_tap()` or classify-then-tap
        itself. A test that genuinely needs to favourite something to prove a
        checklist requirement does so explicitly via `deliberate_tap_at()` in a
        `consequential/` test, using the coordinates returned here — not this method,
        and not `screen_objects/`, which may never import `consequential.py`.

        Returns the price of the listing at `index`, read from the same page_source
        snapshot used to locate the checkbox — not a separate first_listing_price()
        call beforehand. Confirmed live: production's result order can shift between
        two page_source reads even a few seconds apart (D-007's "live inventory
        mutates" risk), so a caller reading the price first and locating the checkbox
        second can end up cross-checking against a different listing than the one
        actually acted on."""
        elements = self.current_elements()
        candidates = [el for el in tappable(elements, include_nested=True)
                      if el.resource_id == self.FAVOURITE_CHECKBOX]
        assert len(candidates) > index, (
            f"expected at least {index + 1} favourite checkbox(es), found {len(candidates)}"
        )
        target = candidates[index]
        prices = [el for el in elements if el.resource_id == self.PRICE_TV]
        price = prices[index].text if len(prices) > index else None

        center = target.center
        assert center is not None, f"favourite checkbox at index {index} has no usable bounds"
        return price, center
