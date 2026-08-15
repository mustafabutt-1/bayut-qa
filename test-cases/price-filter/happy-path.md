# Price Filter — Happy Path

Primary flow per entry point. Two observed entry points (E1, E2), so two primary flows.

---

```gherkin
@feature:price-filter @type:happy @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:observed
Scenario: The price range sheet opens from the LPV quick-filter chip
  Given the app is on the property results screen
  When the "Price" quick filter is opened
  Then the price range sheet is shown
  And the minimum field shows "0"
  And the maximum field shows "Any"
  And the currency label shows "(AED)"

# Expected-result source: context/page_source/en-GB-737ce49f1ddb.xml, build 15.7.2 (1272) —
# selection_title_currency text="(AED)", range_et_min text="0", range_et_max text="Any"
```

---

```gherkin
@feature:price-filter @type:happy @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: A price range narrows the result set
  Given the app is on the property results screen
  And the purpose is set to "Rent"
  When the price range is set to 80,000 to 120,000
  And the price range is applied
  Then no listing priced above 120,000 appears in the results

# Expected-result source: [ASSUMED — needs verification] — cycle 2, fixes B1/B2/B4.
# B1: the previous "probe P6" citation was fabricated; tools/prober.py implements P1–P5
#     only and context/filter-behaviour.md does not exist. No probe has run against this app.
# B2: "the result count matches the API totalCount" removed — no API oracle exists
#     (tools/oracle.py unbuilt, MITM_ENABLED=false), so no tester or tool can observe it.
#     Tracked instead as a blocked case in _feature.md "Blocked on the API oracle".
# B4: "the results are filtered to that range" restated the When; replaced with the
#     falsifiable relational form used in edge-cases.md.
```

---

```gherkin
@feature:price-filter @type:happy @priority:P2 @platform:android
@entry:full-filters-sheet @source:observed
Scenario: The price section is reachable on the full filters sheet
  Given the app is on the property results screen
  When the full filters sheet is opened
  Then a price selection section is shown

# Expected-result source: context/page_source/en-GB-200fe0593bc8.xml —
# group_price_selection and filter_range_input_container present on the filters sheet
```

---

```gherkin
@feature:price-filter @type:happy @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: A applied price range survives back-navigation from a listing
  Given the app is on the property results screen
  And the price range is set to 80,000 to 120,000 and applied
  When the first listing is opened
  And the user navigates back to the results
  Then the price range 80,000 to 120,000 is still applied

# Expected-result source: [ASSUMED — needs verification] — filter persistence across
# DPV back-navigation has never been probed. E6 is an OBSERVED entry point
# (context/screen-flows.observed.md:74) but its filter-retention behaviour is not.
```

---

```gherkin
@feature:price-filter @type:happy @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:observed
Scenario: Applying the sheet returns to the results screen
  Given the price range sheet is open
  When the price range is applied
  Then the property results screen is shown

# Expected-result source: tests/screen_objects/price_range_sheet.py::apply() returns
# PropertiesResultsScreen; asserted live by
# tests/suites/11_filters_search/test_filters_search.py::test_price_range_picker (passing)
```
