# Price Filter — Negative

Invalid input, unreachable state, offline, empty result set. Each case must be
*triggerable* — a negative case nobody can reach is not a test case.

---

```gherkin
@feature:price-filter @type:negative @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: An inverted range is rejected or normalised
  Given the price range sheet is open
  When the minimum is set to 120,000
  And the maximum is set to 80,000
  And the price range is applied
  Then the filter is not applied in its inverted form

# Expected-result source: [ASSUMED — needs verification] — filter-inventory.md lists
# price_band "inverted" as a negative case but records no observed behaviour. Whether the
# app clamps, swaps, blocks Apply, or applies an empty filter is unknown.
```

---

```gherkin
@feature:price-filter @type:negative @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: A range matching no listing shows an empty state rather than an error
  Given the app is on the property results screen
  When the price range is set to 1 to 2
  And the price range is applied
  Then an empty result state is shown
  And no error dialog is shown

# Expected-result source: [ASSUMED — needs verification] — no empty-state element has
# been observed; context/element-inventory.json has no empty-state resource-id for the LPV.
```

---

```gherkin
@feature:price-filter @type:negative @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: Non-numeric input is rejected by the price fields
  Given the price range sheet is open
  When "abc" is entered into the minimum field
  Then the minimum field does not accept the value

# Expected-result source: [ASSUMED — needs verification] — range_et_min is an EditText
# (context/page_source/en-GB-737ce49f1ddb.xml) but its inputType was not captured in the
# dump, so keyboard restriction is unverified.
```

---

```gherkin
@feature:price-filter @type:negative @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: Applying a price filter while offline surfaces a connectivity state
  Given the device has no network connection
  And the app is on the property results screen
  When the price range is set to 80,000 to 120,000
  And the price range is applied
  Then a no-internet state is shown with a retry affordance

# Expected-result source: [ASSUMED — needs verification] — docs/REGRESSION-CHECKLIST.md
# §24 states a "No Internet" screen should show a Retry button, but §24 is a human-authored
# requirement, not an observation of this build.
```

---

```gherkin
@feature:price-filter @type:negative @priority:P3 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: The maximum accepts a value above the documented ceiling
  Given the price range sheet is open
  And the purpose is set to "Buy"
  When the maximum is set to 999,000,000
  And the price range is applied
  Then the filter is applied without error

# Expected-result source: [ASSUMED — needs verification] — filter-inventory.md F5 documents
# a Buy range of 0 → 100,000,000+ but is itself tagged [ASSUMED — verify]; the "+" makes the
# ceiling explicitly open-ended, so this probes past it rather than asserting a hard limit.
```
