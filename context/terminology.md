# Terminology — Bayut / UAE Property Domain

Shared vocabulary so agents write reports a dev, a PM, and a UAE property person all read
the same way. Also the EN↔AR term pairs the Arabic suite asserts against.

**Status:** inferred from the public product and general UAE market usage. All
`[ASSUMED — verify]`, especially the Arabic strings — these must come from the app's own
localisation, not from translation. A wrong expected string produces a false defect.

---

## 1. Product terms

| Term | Meaning | Notes for agents |
|---|---|---|
| **Purpose** | Buy vs Rent | Top-level intent; changes filter set and price semantics |
| **Listing / property** | One advertised unit | Use "listing" in reports for the record, "property" for the physical unit |
| **LDP** | Listing Detail Page | Standard portal shorthand; fine in internal reports |
| **SRP** | Search Results Page | Same |
| **Lead** | A user contacting an agent (call / WhatsApp / email) | **The revenue event.** Say "lead" in severity justifications |
| **TruCheck™** | Bayut's verified-listing programme | A badge that is wrong is a *trust* defect, higher severity than cosmetic `[ASSUMED — verify]` |
| **TruEstimate™** | Property valuation estimate | `[ASSUMED — verify]` present in the Android app |
| **Off-plan** | Under construction, not yet handed over | Contrasted with **Ready** |
| **Ready** | Completed, handed over | — |
| **Handover** | Date the developer delivers the unit | Off-plan listings show a handover quarter/year |
| **Freehold / Leasehold** | Ownership type; freehold areas open to foreign ownership | Relevant to Buy filters `[ASSUMED — verify]` |
| **Rent frequency** | Yearly / Monthly / Weekly / Daily | UAE rent is usually quoted **yearly** — a monthly-looking price is often a defect |
| **Cheques / installments** | Number of rent payments per year (1, 2, 4, 6, 12) | Common UAE listing attribute `[ASSUMED — verify]` in-app |
| **Ejari** | Dubai's tenancy registration system | May appear in content, unlikely in core flows |
| **DLD** | Dubai Land Department | Source of transaction data for market trends |
| **RERA** | Real Estate Regulatory Agency | Listing permit numbers reference it `[ASSUMED — verify]` |
| **Permit / trakheesi number** | Regulatory advert permit shown on listings | Missing permit could be a compliance defect, not just cosmetic `[ASSUMED — verify]` |
| **Community / sub-community / tower** | Location hierarchy below the emirate | The autocomplete hierarchy — get the exact levels right |
| **Agency / agent** | Brokerage and the individual broker | Both have profile pages and their own lead flows |
| **Sqft / sqm** | Area units, user-switchable | 1 sqm = 10.7639 sqft. Conversion errors are a known defect class |
| **AED / Dhs** | UAE dirham | Default currency. Prices are large — formatting and grouping matter |

## 2. Emirates and common areas (for test data selection)

Emirates: Dubai, Abu Dhabi, Sharjah, Ajman, Ras Al Khaimah, Fujairah, Umm Al Quwain,
plus Al Ain as a major city within Abu Dhabi.

High-inventory areas — good defaults for tests that need a non-empty result set
`[ASSUMED — verify]`: Dubai Marina, Jumeirah Village Circle (JVC), Business Bay,
Downtown Dubai, Dubai Hills Estate, Palm Jumeirah, Jumeirah Lake Towers (JLT),
Arabian Ranches, Al Reem Island (AD), Khalifa City (AD), Al Nahda (Sharjah).

Low-inventory areas — good defaults for **empty-state** tests: pick a small
sub-community crossed with an unusual property type. Never hardcode; confirm emptiness at
runtime, since inventory changes daily.

## 3. EN ↔ AR term pairs

**Do not trust this table yet.** Extract the real strings from the app's Arabic build
(`locator-cartographer` in `ar` locale) and replace every row. Asserting on a translated
guess manufactures false defects.

| English | Arabic `[ASSUMED — verify]` | Notes |
|---|---|---|
| Buy | شراء | Purpose toggle |
| Rent | إيجار | Purpose toggle |
| Apartment | شقة | Property type |
| Villa | فيلا | Property type |
| Townhouse | تاون هاوس | Often transliterated |
| Bedrooms | غرف النوم | Filter label |
| Bathrooms | الحمامات | Filter label |
| Studio | استوديو | Beds value |
| Price | السعر | — |
| Area | المساحة | Careful: "area" also means location — different Arabic word (منطقة) |
| Yearly | سنوي | Rent frequency |
| Monthly | شهري | Rent frequency |
| Ready | جاهز | Completion status |
| Off-plan | على الخارطة | Completion status |
| Furnished | مفروش | — |
| Unfurnished | غير مفروش | — |
| Search | بحث | — |
| Filters | الفلاتر / تصفية | Two plausible forms — confirm which ships |
| Call | اتصال | Lead action |
| Email | البريد الإلكتروني | Lead action |
| Save / Favourite | حفظ / المفضلة | — |
| No results found | لم يتم العثور على نتائج | Empty state |

### Arabic-specific test concerns

- **Numerals.** Does the app render Western (`1,250,000`) or Arabic-Indic (`١٬٢٥٠٬٠٠٠`)
  digits in Arabic locale? `UNKNOWN — needs manual verification`. Assertions must match
  the shipped choice, and mixed usage within one screen is itself a defect.
- **RTL mirroring.** Layout, chip order, back-navigation direction, and carousel swipe
  direction all mirror. Icons that should *not* mirror (phone, WhatsApp) sometimes do.
- **Truncation.** Arabic strings are often longer; truncation is the most common RTL
  defect. Test at largest font scale.
- **Mixed-direction strings.** "3 غرف" and prices with Latin currency codes are bidi
  edge cases — rendering order defects hide here.
- **Result-set parity.** Same filters in EN and AR must return the same listings. A
  difference is a defect, not a locale nuance.

## 4. Our internal vocabulary (use these exact words in reports)

| Term | Definition |
|---|---|
| **REAL DEFECT** | The app misbehaved. Evidence supports the test's expectation. |
| **TEST DEFECT** | The test's expectation was wrong. Evidence contradicts the assertion. |
| **LOCATOR DRIFT** | The app is fine; an element identifier changed. |
| **ENVIRONMENT** | Device, network, proxy, build install, or flag state caused the failure. |
| **DATA** | Test data changed under us — expired listing, reset account, empty inventory. |
| **FLAKE** | Non-deterministic, passes on retry, no evidence of a real fault. Must still be logged with evidence — an unexplained flake is a defect we have not understood yet. |
| **Evidence bundle** | The JSON + artefacts `tools/evidence.py` emits for one failure. |
| **Oracle** | An independent source of truth (usually the API) we compare the UI against. |
| **Unverified report** | A generated Markdown defect report awaiting human review. Never a ticket. |
