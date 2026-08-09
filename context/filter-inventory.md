# Filter Inventory — Bayut UAE Android Search

The single largest combinatorial surface in the app, and the direct input to
`tools/pairwise.py`. `test-designer` reads the parameter block below verbatim — keep it
machine-parseable. Prose belongs in the notes columns, not in the block.

**Status:** inferred from the public Bayut UAE product. Every value marked
`[ASSUMED — verify]`. Correct the values *and* the constraints before Phase 1 — a wrong
constraint silently deletes valid combinations from every generated suite.

---

## 1. Filter catalogue

| # | Filter | Control type | Values / range | Interacts with | Notes |
|---|---|---|---|---|---|
| F1 | Purpose | Segmented toggle | `Buy`, `Rent` | F2, F3, F5, F6 | Changes which filters exist at all `[ASSUMED — verify]` |
| F2 | Category | Tab | `Residential`, `Commercial` | F3 | Commercial has its own type list `[ASSUMED — verify]` |
| F3 | Property type | Multi-select list | Residential: `Apartment`, `Villa`, `Townhouse`, `Penthouse`, `Villa Compound`, `Hotel Apartment`, `Residential Plot`, `Residential Floor`, `Residential Building`. Commercial: `Office`, `Shop`, `Warehouse`, `Labour Camp`, `Commercial Villa`, `Bulk Unit`, `Commercial Plot`, `Commercial Floor`, `Commercial Building`, `Factory`, `Showroom`, `Other Commercial` | F2, F4, F7 | `[ASSUMED — verify]` whether multi-select is allowed or single-select only |
| F4 | Location | Autocomplete, multi-select | Emirate → area → community → sub-community/tower. e.g. `Dubai`, `Dubai Marina`, `Marina Gate 1` | — | Hierarchy depth and multi-select cap `[ASSUMED — verify]` |
| F5 | Price min / max | Range, two numeric inputs + presets | AED. Buy: 0 → 100,000,000+. Rent: 0 → 5,000,000+ | F1, F6, F25 | Currency switch must not silently re-scale the filter `[ASSUMED — verify]` |
| F6 | Rent frequency | Segmented | `Yearly`, `Monthly`, `Weekly`, `Daily` | F1, F5 | **Rent only.** Changes the meaning of the price range entirely |
| F7 | Beds | Chip multi-select | `Studio`, `1`–`7`, `7+` | F3 | N/A for plots, warehouses, offices `[ASSUMED — verify]` |
| F8 | Baths | Chip multi-select | `1`–`7`, `7+` | F3 | Same N/A set as beds `[ASSUMED — verify]` |
| F9 | Area min / max | Range + unit | sqft or sqm per F26 | F26 | Unit switch must convert, not relabel — classic defect `[ASSUMED — verify]` |
| F10 | Completion status | Segmented | `Any`, `Ready`, `Off-Plan` | F1 | `[ASSUMED — verify]` Rent shows this at all |
| F11 | Furnishing | Segmented | `Any`, `Furnished`, `Unfurnished` | F1 | `[ASSUMED — verify]` `Partly furnished` exists |
| F12 | TruCheck™ only | Toggle | `on`, `off` | — | Trust filter; a false badge is a credibility defect |
| F13 | Virtual viewings / 360 tour | Toggle | `on`, `off` | — | `[ASSUMED — verify]` |
| F14 | Keyword / free text | Text input | free string | — | Injection-ish edge cases: Arabic text, emoji, very long strings, `"` |
| F15 | Amenities | Multi-select list | `Balcony`, `Parking`, `Shared Pool`, `Private Pool`, `Gym`, `Security`, `Maids Room`, `Study`, `Central A/C`, `Pets Allowed`, `Concierge`, `Built-in Wardrobes`, … | F3 | Full list `[ASSUMED — verify]` — likely 20+ values |
| F16 | Agent / agency | Autocomplete | agency name | — | `[ASSUMED — verify]` present in app filters vs web only |
| F17 | Date added / freshness | Segmented | `Anytime`, `Last 24 hours`, `Last 3 days`, `Last week`, `Last month` | — | `[ASSUMED — verify]` |
| F18 | Sort order | Dropdown | `Default/Popular`, `Newest`, `Price low→high`, `Price high→low`, `Beds most`, `Beds least` | F5 | Not a filter, but pairs with them and is a frequent regression site |
| F19 | Map / list view mode | Toggle | `List`, `Map` | F4 | Map bounds become an implicit location filter |
| F20 | Verified/quality score | Toggle or sort | `[ASSUMED — verify]` | — | May not exist — confirm before including |

### Cross-cutting parameters (not filters, but must vary in the covering array)

| # | Parameter | Values | Why it belongs in the array |
|---|---|---|---|
| F25 | Currency | `AED`, `USD`, `EUR`, `GBP`, `SAR` `[ASSUMED — verify]` | Price display and price filter must stay consistent |
| F26 | Area unit | `sqft`, `sqm` | Conversion vs relabel defects |
| F27 | Locale | `en`, `ar` | RTL layout, Arabic-Indic numerals, truncation |
| F28 | Auth state | `guest`, `logged_in` | Favourites/saved-search behaviour differs |
| F29 | Network | `wifi`, `4g_throttled`, `offline` | Empty vs error vs stale-cache confusion |

---

## 2. Parameter block for `tools/pairwise.py`

Consumed as-is. Keep keys stable — generated case IDs are derived from them.

```yaml
# pairwise input: core residential search
parameters:
  purpose:            [Buy, Rent]
  category:           [Residential, Commercial]
  property_type:      [Apartment, Villa, Townhouse, Penthouse, Office, Warehouse, Residential Plot]
  beds:               [Studio, "1", "3", "7+", Any]
  rent_frequency:     [Yearly, Monthly, Weekly, Daily, N/A]
  price_band:         [none, low, mid, high, inverted]     # inverted = min > max, negative test
  completion_status:  [Any, Ready, Off-Plan]
  furnishing:         [Any, Furnished, Unfurnished]
  trucheck_only:      [true, false]
  area_unit:          [sqft, sqm]
  currency:           [AED, USD]
  locale:             [en, ar]
  auth_state:         [guest, logged_in]
  sort_order:         [Default, Newest, "Price low to high"]

constraints:
  # Each entry is a human-readable rule plus the machine form pairwise.py enforces.
  - id: C1
    rule: "rent_frequency is only meaningful when purpose == Rent"
    expr: "purpose == 'Rent' or rent_frequency == 'N/A'"
  - id: C2
    rule: "rent_frequency must not be N/A when purpose == Rent"
    expr: "purpose != 'Rent' or rent_frequency != 'N/A'"
  - id: C3
    rule: "Commercial category excludes residential property types"
    expr: "category != 'Commercial' or property_type in ['Office', 'Warehouse']"
  - id: C4
    rule: "Residential category excludes commercial property types"
    expr: "category != 'Residential' or property_type not in ['Office', 'Warehouse']"
  - id: C5
    rule: "beds is not applicable to plots, offices, warehouses"
    expr: "property_type not in ['Residential Plot', 'Office', 'Warehouse'] or beds == 'Any'"
  - id: C6
    rule: "completion status Off-Plan does not apply to Rent"      # [ASSUMED — verify]
    expr: "purpose != 'Rent' or completion_status != 'Off-Plan'"
  - id: C7
    rule: "furnishing does not apply to plots"                      # [ASSUMED — verify]
    expr: "property_type != 'Residential Plot' or furnishing == 'Any'"
```

**Sanity target.** Full cross product of the block above is ~1.8M combinations; a
2-wise covering array should land in the low tens of tests. If `pairwise.py` returns
fewer than ~25 rows, a constraint is over-broad and is deleting real combinations —
check before trusting the output. Never hand this arithmetic to a model.

---

## 3. Filter behaviours that need explicit assertions

Each of these is a defect class we have seen in property portals generally. All
`[ASSUMED — verify]` for Bayut specifically — confirm, then promote the confirmed ones
into `known-behaviors.md`.

1. **Result-count truthfulness.** Header count must equal the count the API returned,
   and the rendered list must contain every returned ID. → `tools/oracle.py`, our
   highest-value automated check.
2. **Filter persistence.** Filters survive: back navigation, LDP round-trip, app
   backgrounding, locale switch, and rotation. Losing filters on back is the single most
   commonly reported portal defect.
3. **Filter chip ↔ state parity.** Chips shown above results must match applied state
   exactly. Removing a chip must remove exactly one filter.
4. **Reset / Clear all.** Returns to a genuinely default state, including hidden filters
   the user never opened.
5. **Zero results.** Shows a real empty state with a route out, not a spinner, not a
   stale previous result set.
6. **Inverted range.** min > max is prevented, corrected, or explained — never silently
   returns everything.
7. **Unit conversion.** sqft↔sqm converts the *value*, does not just swap the label.
8. **Currency conversion.** Same, for price — and the filter range must convert with it.
9. **Arabic locale.** Numerals, RTL chip order, no truncation, and identical result sets
   to `en` for the same filter state. **A result-set difference between locales is
   always a defect.**
10. **Deep-link → filter state.** A URL with filter params lands on the same state the UI
    would produce. This is also how `flow-builder` sets up tests — if it breaks, the
    suite breaks.
11. **Pagination under filter.** Page 2 respects the filters. Classic backend defect.
12. **Sort stability under filter.** Sorting does not drop or duplicate listings across
    page boundaries.

---

## 4. Open questions blocking the covering array

- `UNKNOWN — needs manual verification`: is property type single- or multi-select? Changes
  the parameter model from enum to power-set.
- `UNKNOWN — needs manual verification`: do filters apply live, or only on "Show N
  properties"? Determines whether an intermediate assertion is even legal.
- `UNKNOWN — needs manual verification`: exact amenity list and whether amenities are
  AND-ed or OR-ed. AND vs OR changes every expected result.
- `UNKNOWN — needs manual verification`: which filters are server-side vs client-side.
  Client-side filters cannot be checked with the API oracle.
- `UNKNOWN — needs manual verification`: is there a max on multi-select locations/types?
- `UNKNOWN — needs manual verification`: are any filters behind a remote feature flag?
