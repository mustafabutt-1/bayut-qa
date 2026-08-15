# Price Filter — Edge Cases

Boundaries, zero, max, locale switch mid-flow, interruption, back-navigation state, RTL.

---

```gherkin
@feature:price-filter @type:edge @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: Price filter includes listings at the upper bound
  Given the app is launched with a cleared filter state
  And the purpose is set to "Rent"
  And the location is set to the sanctioned test location
  And at least one listing priced at exactly 120,000 exists in the unfiltered results
  When the price range is set to 80,000 to 120,000
  And the price range is applied
  Then that listing still appears in the results

# Expected-result source: [ASSUMED — needs verification] — cycle 2, fixes B1/B5.
# B1: the previous "probe P6, 2026-08-11" citation was fabricated. tools/prober.py
#     implements P1–P5 only; there is no boundary-inclusivity probe and
#     context/filter-behaviour.md does not exist. Upper-bound inclusivity is UNKNOWN.
# B5: no longer asserts that live inventory contains a listing at exactly the bound.
#     The listing is now a Given — a precondition the tester establishes by reading the
#     unfiltered results first, and skips if unmet. This keeps the case executable
#     against inventory that mutates daily (D-007) while still testing the boundary.
# Location: "Dubai Marina" was replaced with the sanctioned test location — production
# testing must stay on the QA team's own data (tests/test_data.py, docs/GUARDRAILS.md §3).
```

---

```gherkin
@feature:price-filter @type:edge @priority:P1 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: Price filter excludes listings above the upper bound
  Given the app is on the property results screen
  And the purpose is set to "Rent"
  When the price range is set to 80,000 to 120,000
  And the price range is applied
  Then no listing priced above 120,000 appears in the results

# Expected-result source: [ASSUMED — needs verification] — no boundary probe exists
# (P1–P5 only). Stated as a relational assertion ("none above") rather than an existence
# assertion, so it is executable against live inventory that mutates daily (D-007).
```

---

```gherkin
@feature:price-filter @type:edge @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:observed
Scenario: The maximum field defaults to a non-numeric "Any"
  Given the app is launched with a cleared filter state
  When the "Price" quick filter is opened
  Then the maximum field shows "Any"

# Expected-result source: context/page_source/en-GB-737ce49f1ddb.xml —
# range_et_max text="Any" hint="Any", an EditText whose default is a word, not a number.
```

---

```gherkin
@feature:price-filter @type:edge @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario Outline: Boundary values are accepted by the price fields
  Given the price range sheet is open
  When the minimum is set to <minimum>
  And the maximum is set to <maximum>
  And the price range is applied
  Then the applied range reads <minimum> to <maximum>

  Examples:
    | minimum | maximum |
    | 0       | 0       |
    | 0       | 1       |
    | 1       | 1       |

# Expected-result source: [ASSUMED — needs verification] — zero and equal-bound handling
# is unprobed. Covered as an Outline because the three rows differ only in data.
```

---

```gherkin
@feature:price-filter @type:edge @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: Switching to Arabic keeps the applied price range numerically identical
  Given the price range 80,000 to 120,000 is applied
  When the app language is switched to Arabic
  Then the applied price range is still 80,000 to 120,000

# Expected-result source: [ASSUMED — needs verification] — filter-inventory.md F27 flags
# Arabic-Indic numerals as a defect class; no locale switch has been performed on this build.
# context/terminology.md warns its Arabic strings are translations, not the app's own,
# so no Arabic label may be asserted here.
```

---

```gherkin
@feature:price-filter @type:edge @priority:P2 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: The price sheet survives a backgrounding interruption
  Given the price range sheet is open with 80,000 entered as the minimum
  When the app is sent to the background
  And the app is brought back to the foreground
  Then the price range sheet is still open with 80,000 as the minimum

# Expected-result source: [ASSUMED — needs verification] — the crawler resets rather than
# backgrounds (E5 is UNRESOLVED in _feature.md), so this path has never been observed.
```

---

```gherkin
@feature:price-filter @type:edge @priority:P3 @platform:android
@entry:lpv-quick-filter-chip @source:assumed
Scenario: An entered minimum survives device rotation
  Given the price range sheet is open with 80,000 entered as the minimum
  When the device is rotated to landscape
  Then the minimum field still shows 80,000
  And the apply control is still reachable

# Expected-result source: [ASSUMED — needs verification] — cycle 2, fixes B3.
# The previous "Then the price filter still works correctly" was unfalsifiable: nothing
# stated what observation would fail it. Rotation is worth testing — an EditText losing
# its value on configuration change is a real defect class — so the case is kept and
# given two observable assertions instead of being deleted.
# No rotation has been performed on this build; the crawler does not rotate.
```
