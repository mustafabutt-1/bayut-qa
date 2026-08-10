# Regression Checklist — Ground Truth

Extracted from **"Bayut UAE Regression Checklist"** (PDF, supplied by the QA lead
2026-08-09). This is the team's own document, so it is **evidence, not inference** — it
outranks every `[ASSUMED — verify]` hypothesis in `feature-map.md`,
`filter-inventory.md`, `screen-inventory.md` and `terminology.md`.

**Credentials warning.** The source PDF contains six sets of live test-account
credentials. They are deliberately **not reproduced here**. Store them in `.env`
(gitignored) and reference by variable name. See `docs/GUARDRAILS.md` §4.

Tag: `[OBSERVED — regression checklist 2026-08-09]` throughout. Where the checklist is
silent, the item stays UNKNOWN rather than being filled in.

---

## 1. Corrections to my Phase 0 hypotheses

These were wrong. Fixed here; the source files still need updating.

| # | I assumed | Checklist says | Impact |
|---|---|---|---|
| 1 | Search results = **SRP**, detail = **LDP** | **LPV** (listings page view) and **DPV** (detail page view) | `terminology.md` is wrong. Every report, screen object and agent must use LPV/DPV or dev will not recognise our vocabulary. |
| 2 | Locales are **EN + AR** | **English, Arabic, Russian, Chinese** | The `arabic` pytest marker is too narrow. Four locales, three of them non-English. Russian and Chinese are not RTL but do have length/truncation risk. |
| 3 | Sort options include "Beds most/least" | **TruCheck, Popular, Newest, Price low→high, Price high→low** | My `filter-inventory.md` F18 values are wrong. |
| 4 | Emirates list is 7 + Al Ain as part of Abu Dhabi | **8 shown in Popular**: Dubai, Abu Dhabi, Sharjah, Ajman, Ras Al Khaimah, **Al Ain**, Umm Al Quwain, Fujairah | Al Ain is a first-class location in the picker. |
| 5 | Max multi-select locations UNKNOWN | **Maximum 5 locations** on the search results page | Real constraint for `pairwise.py`. |
| 6 | Beds/Baths N/A for plots/offices was a guess | **Confirmed**: Beds and Baths must not appear on Filters screen, Filters bar or LPV inline filters for **Commercial** property type — but bed/bath counts *can* still appear on property cards | Constraint C5 is real, and there is a subtle assertion: filter hidden ≠ data absent. |
| 7 | Bottom nav = Home/Search/Favourites/Profile | **Home, Properties, Transactions, TruEstimate, More** | `screen-inventory.md` navigation model is wrong. |
| 8 | Result count should exactly match the API | **"Slight difference in property count between platforms is expected due to Algolia's continuous background synchronisation"** | **Directly affects `oracle.py`.** See §4. |
| 9 | TruCheck is a Tier-2 trust badge | TruCheck is a **sort option and a filter toggle and a banner**, and sits alongside TruBroker/Checked/Off-Plan badge families | Promote to Tier 1 in `feature-map.md`. |

---

## 2. Feature areas the checklist reveals that I never had

My 36-area map missed these entirely. All are substantial, several are business-critical.

| Area | Notes |
|---|---|
| **Dubai Transactions (DT)** | Own home screen, map view, filters, share links, Claim Transactions (agent + admin flows), Share Transactions (max 30, PDF export 15/page). Location-restricted to Dubai and children. |
| **BayutGPT** | LLM assistant. Entry points: Home banner, LPV widget at position 3. Chat history persists across app kill, clears on logout. Hidden for non-English locales. **Costs money per query.** |
| **TruEstimate™** | Standard reports, Branded reports (TruBroker agents), Portfolio, Alerts. Generation via Unit Number / Title Deed / Oqood / Dewa / Contract Number. Own bottom-nav tab. |
| **TruBroker™ & Find My Agent** | Agent/agency directory, leaderboard, TruPoints, badges (TruBroker, Quality Lister, Responsive Broker). Widget at LPV position 1. |
| **TruBroker Stories** | Instagram-style stories, Dubai and Abu Dhabi only, with share-to-social and deep links. |
| **Off-Plan Projects** | Project LPV, Projects list, Projects FAB, project-specific filters (Handover By, Payment Plan, % Completion). |
| **Commute Based Search (Search 2.0)** | Travel-time search, single or dual locations. |
| **Activity Log** | Recent Searches / Viewed / Contacted. |
| **Notification Center** | Master toggle → phone settings, five MoEngage custom attributes. |
| **Area Prime Slot** | Premium top-of-results slot in Loc3+ (Business Bay, Downtown, JVC). Marked **business critical**. Replaced "Deal of the Week". |
| **Regulatory Information** | Trakheesi, Zone Name, RERA, BRN, Madhmoun, ADM, CPL, BLN, ORN, DRER, RAKEZ. Compliance surface. |
| **Analytics verification** | Firebase, MoEngage, Adjust (deferred deeplinks), GA4 events. |
| **Firebase Crashlytics review** | Fatal + non-fatal reviewed **before sign-off**. |

---

## 3. Structural facts worth encoding

### Inline widget positions on LPV — fixed and assertable
| Widget | Position |
|---|---|
| TruBroker | after listing 1 |
| BayutGPT | after listing 3 |
| TruEstimate | after listing 7 |
| Dubai Transactions | after listing 10 |

Only widgets *containing data* are visible — so absence is not automatically a defect.

### Location hierarchy
`Loc 0 = UAE` → `Loc 1 = Dubai, Abu Dhabi, …` → Loc 2 → Loc 3. Seventeen screens have
**different** location-level restrictions (LPV none; DT Dubai-only; Seller Leads Loc3+;
Search 2.0 Loc1 and below; TruEstimate Loc2/Loc3 under Dubai; …). This is a rich source
of boundary defects and a natural `pairwise.py` parameter.

### Badge families
TruBroker, TruCheck, Checked, Off-Plan, Off-Plan Initial Sale, Off-Plan Resale. Tapping a
badge or Viewed/Contacted opens a bottom sheet. Badge bottom sheets differ for a
logged-in agent viewing **their own** listing.

### Filter surfaces — seven distinct screens
Properties, New Projects, Commute (Search 2.0), MapView, Dubai Transactions,
Recommended Properties Link, Remarketing Link. My `filter-inventory.md` modelled **one**.

### Filter entry points — four
Filters screen, Quick Filters Bar, LPV Inline filters, Previously Applied bottom sheet.
Parity between these four is an obvious defect class.

### Devices
Android **16 and 8–10** — a very wide span, and 8–10 is where ANRs and layout truncation
live. Android regression also requires a **Fold** device, folded and unfolded, with state
continuation across the transition.

---

## 4. What this changes for `oracle.py`

The checklist states plainly that property counts differ between app and web because of
Algolia background synchronisation.

**This does not invalidate the oracle, but it narrows it.** The valid comparison is
*within a single request*: the API response the app received versus what that same app
render displays. Comparing app to web, or one run to another, is comparing across Algolia
syncs and will produce false positives.

Encoded as a hard rule for `oracle.py` when it is built:

> Compare only the HAR entry that produced the currently rendered screen against that
> screen. Never compare against web, a previous run, or a re-query.

The checklist also hands us a genuine oracle-able assertion:

> "Ensure that the TraceID in the link generated by WhatsApp/SMS leads exactly matches
> the `event_unique_id` in the `whatsapp_lead` and `sms_lead` events."

That is an exact string match between a UI-generated link and an analytics event —
deterministic, checkable, and currently manual.

---

## 5. Test data (values only — credentials live in `.env`)

| Purpose | Value |
|---|---|
| Test location for lead verification | **Al Napoca** |
| Test agency for lead verification | **Explorer Real Estate** |
| Test portfolio account | `$TEST_PORTFOLIO_EMAIL` / `$TEST_PORTFOLIO_PASSWORD` |
| Admin accounts (2) | `$TEST_ADMIN_1_EMAIL` / `$TEST_ADMIN_1_PASSWORD`, `$TEST_ADMIN_2_*` |
| Agent accounts (2) | `$TEST_AGENT_1_*`, `$TEST_AGENT_2_*` |

Both Al Napoca and Explorer Real Estate are wired into `tools/crawl_safety.py` as
`LEAD_TEST_LOCATION` and `LEAD_TEST_AGENCIES`.

---

## 6. Regression realities that constrain automation

- **Regression builds use Production configuration across the board** — APIs, Firebase,
  MoEngage, Humbucker. This is the checklist's own statement, and it is why
  `docs/GUARDRAILS.md` defaults to production.
- Four install scenarios must be covered: Fresh Install, Override (logged out), Override
  (logged-in consumer), Override (logged-in agent). Override testing needs a prior build
  installed — automatable, but it needs two APKs and careful `pm install -r`.
- **Mock location** is required for "Lookup Nearby Locations" (Fake GPS on Android).
  Automatable via `adb shell appops`/mock-location provider, but needs verification.
- **Adjust deferred deeplinks** require the Adjust testing console and clearing device
  data by Advertising ID. **Not automatable by us** — external console, manual.
- **Firebase/MoEngage event verification** requires console access. Partially automatable
  if events also appear in mitmproxy traffic; otherwise manual.
- **Crashlytics review before sign-off** is a `production-signal` agent input, not a
  test-suite output.

---

## 7. Actions this creates

- [ ] Rewrite `terminology.md`: SRP→**LPV**, LDP→**DPV**, add TruCheck/TruBroker/Checked,
      Trakheesi, Oqood, Dewa, Madhmoun, DLD, RERA, BRN, ORN, Nova, Algolia, Humbucker.
- [ ] Rewrite `feature-map.md`: add the 13 areas in §2, correct the bottom nav, promote
      TruCheck and Area Prime Slot to Tier 1.
- [ ] Rewrite `filter-inventory.md`: correct sort values, add the 5-location cap, add the
      Commercial→no-Beds/Baths constraint as **confirmed**, model seven filter surfaces
      rather than one, and add location-level as a parameter.
- [ ] Extend the locale axis from `en, ar` to `en, ar, ru, zh`; rename the `arabic`
      pytest marker to `i18n` with a locale parameter, or add `rtl` separately.
- [ ] Add `docs/ASKS.md` line: a staging environment is what unlocks the write-path
      coverage this checklist is mostly made of.
- [ ] Reconcile the 144 Testmo cases against this checklist — they may already overlap
      heavily, which would make the reconciliation much cheaper than expected.

**None of these are done yet.** They are the corrections the checklist forces, recorded
so they are not lost, and they should be applied before any test design work.
