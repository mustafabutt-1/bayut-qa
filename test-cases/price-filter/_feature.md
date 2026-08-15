# Feature: Price Filter

- **Slug:** `price-filter`
- **Written by:** `feature-test-designer`, cycle 1
- **Date:** 2026-08-12
- **Build under test:** 15.7.2 (1272) — `.env` `BAYUT_BUILD_VERSION`
- **Checklist section:** §11 Filters & search (`docs/REGRESSION-CHECKLIST.md`)

---

## Mapping state: PARTIALLY MAPPED

| Aspect | State | Source |
|---|---|---|
| Screens | `[OBSERVED]` | `context/page_source/en-GB-737ce49f1ddb.xml`, `context/screen-inventory.observed.md` |
| Elements | `[OBSERVED]` | `context/element-inventory.json` |
| Entry points | `[OBSERVED]` ×2 | `context/screen-flows.observed.md:57` |
| **Behaviour** | **NOT PROBED** | `context/filter-behaviour.md` **does not exist**; `context/known-behaviors.md` has **0** confirmed entries |

**Consequence:** every *behavioural* expectation in this case set is
`[ASSUMED — needs verification]`. Structure, labels and defaults are cited from real page
source. Nothing here claims to know what the filter *does* to a result set, because no
probe has ever been run against this app.

### Probes needed but unavailable

`tools/prober.py` implements **P1–P5 only** (verified: `grep -n 'ProbeResult("P' tools/prober.py`):

| Probe | Answers | Relevant here |
|---|---|---|
| P1 | cardinality (single vs multi select) | No — price is a range, not an option set |
| P2 | apply mode (live vs explicit Apply) | **Yes** — not yet run |
| P3 | AND/OR across options | No |
| P4 | constraint (A blocks B) | Marginal |
| P5 | filter existence vs `filter-inventory.md` | **Yes** — not yet run |

**There is no boundary-inclusivity probe.** The single most important expected result for
a range filter — *is the upper bound inclusive?* — cannot be answered by current tooling.
It needs either a manual check or a new probe (`P6`, unimplemented). Every bound-related
expectation below is therefore `[ASSUMED — needs verification]`, and the covering array
deliberately includes `zero_max` and `inverted` bands so the gap is visible rather than
silently skipped.

---

## Scope

**In scope** — the Price Range control itself:

- The `PriceRangeSheet` bottom sheet (`price_range_selector`), reached from the LPV
  quick-filter chip
- The inline price section on the full Filters sheet (`group_price_selection`)
- Min/max entry, defaults, Apply, and the effect on the result set
- Currency label rendering and locale/RTL behaviour of the numeric inputs

**Out of scope:**

- Area range (`F9`) — same range-widget shape, separate feature
- Sort by price (`F18`) — pairs with this filter but is its own feature
- The API oracle (`tools/oracle.py` is not built; `docs/PROJECT-STATE.md` §2). Result
  counts cannot currently be cross-checked against an API response by tooling.

---

## Entry points

| # | Entry point | State | Evidence |
|---|---|---|---|
| E1 | LPV quick-filter chip "Price" → `PriceRangeSheet` | `[OBSERVED]` | `context/screen-flows.observed.md:57` — `Properties -->｜open_price_range_picker()｜ PriceRange` |
| E2 | Full Filters sheet → inline price section | `[OBSERVED]` | `group_price_selection`, `filter_range_input_container` in `context/page_source/en-GB-200fe0593bc8.xml` |
| E3 | Deep link into a pre-filtered search | `[UNRESOLVED]` | `BAYUT_DEEPLINK_SCHEME` is blank in `.env`; no deep link has ever been exercised |
| E4 | Push-notification landing on a filtered LPV | `[UNRESOLVED]` | No push tooling; `docs/REGRESSION-CHECKLIST.md` §25 is manual |
| E5 | Return-from-background with a filter applied | `[UNRESOLVED]` | Not crawled; the crawler resets rather than backgrounds |
| E6 | Back-navigation from DPV into a filtered LPV | `[OBSERVED]` | `context/screen-flows.observed.md:74` — `DPV -->｜go_back()｜ Properties` |

E3–E5 are declared gaps, not omissions. E3 in particular is worth building: a deep link
is the cheapest way to reach a filtered state deterministically, which is what makes the
boundary cases executable (see `negative.md` preconditions).

---

## Observed facts the cases rely on

All from `context/page_source/en-GB-737ce49f1ddb.xml` (PriceRangeSheet, build 15.7.2):

| Element | resource-id | Observed |
|---|---|---|
| Sheet title | `selection_title_tv` | text `"Price Range"` |
| Currency label | `selection_title_currency` | text `"(AED)"` |
| Minimum input | `range_et_min` | `EditText`, text `"0"`, hint `"0"`, label `"Minimum"` |
| Maximum input | `range_et_max` | `EditText`, text `"Any"`, hint `"Any"`, label `"Maximum"` |
| Separator | `to_tv` | text `"to"` |
| Apply | `confirm_tv` | text `"Apply"` |
| Slider | `view_range_bar` | present |

Two things follow that the cases use directly:

1. **The maximum defaults to the string `"Any"`, not a number.** Any expectation about
   "no upper bound" behaviour must account for a non-numeric default.
2. **An `Apply` control exists**, so the sheet is structurally an explicit-apply filter.
   Whether the result count updates *before* Apply is a P2 question and is unprobed.

---

## Blocked on the API oracle

One assertion was removed from `happy-path.md` in cycle 2 (audit item B2) and is parked
here rather than deleted, because it is a real requirement that simply cannot be executed
yet:

> **Result-count truthfulness.** The header count must equal the count the API returned.
> `context/filter-inventory.md` §3 lists this first among filter behaviours needing
> explicit assertions.

Blocked by: `tools/oracle.py` is not built (`docs/PROJECT-STATE.md` §2, deliberately
waiting on the pinning verdict), `MITM_ENABLED=false` and `API_BASE_HOST` is blank in
`.env`. Neither a human on a device nor any current tooling can observe `totalCount`.

Unblocks when: mitmproxy is configured and the certificate-pinning question is answered
(`context/pinning-check.md` currently reports `MITM_NOT_CONFIGURED`).

---

## Sanctioned test data

Production testing uses the QA team's own data only (`docs/GUARDRAILS.md` §3,
`tests/test_data.py`): location **Al Napoca**, agency **Explorer Real Estate**. Cycle 1
used "Dubai Marina" in one scenario, which browses a real brokerage's live inventory;
corrected in cycle 2.

---

## Dependencies

- `tests/screen_objects/price_range_sheet.py` — `MIN_INPUT`, `MAX_INPUT`, `APPLY`
- `tools/pairwise.py` — covering array (`_pairwise-model.yaml`)
- **Safety:** the price sheet contains no lead control. `PROD-BLOCK-SAVE-SEARCH` blocks
  "Save this search" on the LPV behind it — cases must not save a search.

---

## Declared coverage gaps

Carried forward from `_audit.md` cycle 1. Declared, not omitted — each is a decision
someone can act on:

| Gap | Why it is open |
|---|---|
| **E2 under-covered** (audit A3) | The covering array assigns `entry_point=full_filters_sheet` to 8 of 30 rows, but only one scenario is tagged `@entry:full-filters-sheet` and it asserts only that the section is present. Needs a real E2 apply-and-assert case in the next writing pass — the revision protocol forbids adding scenarios mid-revision. |
| **Price slider untested** | `view_range_bar` is present in the observed page source alongside the two `EditText`s. Text entry and slider entry may disagree — a classic range-widget defect — and no case covers the slider at all. |
| **Clear/reset untested** | No case clears an applied price range. "Filter persists when it should have cleared" is a common regression, and the LPV has a reset affordance. |
| **E3 deep link** | `BAYUT_DEEPLINK_SCHEME` is blank in `.env`; nothing can exercise it. Worth building — a deep link is the cheapest way to reach a filtered state deterministically, which would make several boundary cases executable. |
| **E4 / E5** | Push landing and return-from-background have no tooling; E5 has an assumed edge case written against it, E4 has none. |

---

## Out-of-scope risks worth naming

- **Live production inventory mutates** (D-007). Any case asserting "a listing at exactly
  X exists" is not reliably executable. Cases below prefer relational assertions
  ("no listing above the maximum") over existence assertions where possible.
- `context/element-inventory.json` was last rebuilt by `crawler.py offline`, which records
  `App: vOFFLINE (UNKNOWN)` rather than a build number. The underlying page-source
  captures are from 15.7.2 (1272), but the inventory header cannot prove it.
