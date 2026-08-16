# Bayut UAE

**Status:** Complete — config, vocabulary, domain, and regression-critical areas populated from the DPV suite and the Bayut UAE regression checklist.
**Platforms:** iOS, Android (native)
**Testmo project ID:** 38 (site: dubizzlelabs.testmo.net)

This file is the quality bar for the other app knowledge bases — match its depth. Everything is evidenced from the DPV In-App Survey work or the Bayut UAE regression checklist unless marked TODO.

---

## A. Configuration

| Setting | Value |
| --- | --- |
| Testmo project ID | **38** |
| Features repo | `/repositories/38?group_id=79014` — create a new folder per feature under group **79014** |
| Case template | TODO — confirm (Case text / steps / BDD) |
| Primary market(s) | United Arab Emirates |
| Bundle IDs (iOS / Android) | TODO |

### Languages

| Code | Language | RTL | Notes |
| --- | --- | --- | --- |
| EN | English | No | Default |
| AR | Arabic | **Yes** | Full RTL: mirrored layout, chevron and icon direction, sheet slide direction |
| ZH | Chinese | No | Strings run short — watch for gaps and misaligned centring |
| RU | Russian | No | Strings run long — the main truncation and overlap risk |

All four are mandatory for localisation cases. Currency and Area Unit are also switchable from Settings and must be verified app-wide (they affect LPV cards, DPV, Activity Log, Dubai Transactions). Note: BayutGPT entry points are **English-only** — hidden in AR/RU/ZH.

Copy sheets: [Bayut.com Copy Requirements](https://docs.google.com/spreadsheets/d/1B5Im8KPe0zqvznFb4noUF6YwdoNGlLYvxW-GMfLpISU/edit), [Bayut App Copy Requirements](https://docs.google.com/spreadsheets/d/1wlF5Nn1kYS19VWgvBA9IpX_bLUUOZn0frwcVuoLtGng/edit).

### Device matrix

| Platform | Devices |
| --- | --- |
| iOS | iPhone (latest + older OS), **iPad** (Portrait and Landscape — mandatory smoke), mini-screen |
| Android | Phone (latest + older OS), **Fold** (folded, unfolded, and the fold transition with state continuation), low-end |

### Minimum supported OS

Per the current checklist: **iOS 26, 18, 17, 16** and **Android 16, 10, 9, 8**. Confirm each cycle — these move.

### Analytics

Platform: GA4 via Firebase; MoEngage for push. Events tracking sheet: [Bayut GA4 Tracking Requests](https://docs.google.com/spreadsheets/d/1oNncXiJxUhB6Zcgnn8IoLicAnRDNn91CxTCItsmvGC4/edit).

Known constraints and recurring checks:
- Event-scoped custom-dimension values cap at **100 characters**, truncated silently above — free-text to GA needs a boundary case.
- The `listing_pagetype` parameter value must be verified for LPV/DPV/lead events.
- WhatsApp/SMS leads: the **TraceID** in the generated link must exactly match `event_unique_id` in the `whatsapp_lead` / `sms_lead` events.
- MoEngage push events (Sent, Received, Clicked, Dismissed) must be verified in **both killed and background** states.
- Rapid or repeated interaction must not fire duplicate events.

### Remote config

Platform: Firebase Remote Config. Flags are snake_case booleans, e.g. `is_dpv_survey_enabled`. Always cover flag on, flag off, flag missing/malformed, and toggling while the app runs. Several thresholds are remote-config driven (e.g. App Review appears after N sessions — currently 5).

Regression builds must run **Production configs across the board** (APIs, Firebase, MoEngage, Humbucker). With Firebase App Check configured in Production, the hCaptcha fallback loader seen on Stage should **not** appear in ~99%+ of Production sessions — its appearance in a regression build is itself a defect signal.

---

## B. Vocabulary

| Term | Meaning |
| --- | --- |
| DPV | Property detail view — a single listing |
| LPV | Listing page view — search results |
| Homepage banners | The rotating promotional widget at the top of the homepage (TruEstimate, Portfolio, Dubai Transactions, Propco, TruBroker, etc.) — team term, corrects the earlier "promotional banner carousel" phrasing |
| Gallery View | Full-screen image gallery opened from the DPV |
| MapView | Map-based search results |
| CBS / Search 2.0 | Commute-Based Search — search by travel time to one or two locations |
| DT | Dubai Transactions |
| Purpose | Sale/Buy or Rent — the listing's transaction type |
| Lead | A contact action on a listing (Email, Phone, SMS, WhatsApp) |
| Nudge / bottom sheet | A prompt sheet (App Review, survey, badge explanations) |
| Fat card / lean card | Rich listing card vs compact card (MapView uses lean cards) |
| Area Prime Slot | Premium top-of-results listing slot in L3+ locations (replaced "Deal of the Week") |
| TruBroker / TruCheck / TruEstimate | Agent-ranking programme / verified-listing badge / property valuation report product |
| Loc level 0/1/2/3 | Location hierarchy: 0 = UAE, 1 = emirate, 2/3 = child locations |

---

## C. Product domain

- **Vertical:** Residential and commercial property, Sale and Rent, plus Off-Plan (New Projects).
- **Core value exchange:** a **lead** — the user contacting an agent via Email, Phone, SMS, or WhatsApp. Lead generation is the primary conversion and the trigger for several features (App Review nudge, the DPV survey, Adjust deferred-deeplink events).
- **Who posts and who consumes:** agents and agencies list (with two POVs — end-user and agent — across many screens); buyers and renters browse and generate leads. **Agent vs end-user POV is a pervasive test dimension**: leaderboards, badge bottom sheets, TruEstimate branded reports, and Find My Agent all render differently for agents viewing their own listings.
- **Structurally notable:** the same DPV serves Sale and Rent via *Purpose*, and features frequently attribute behaviour to the Purpose of the *originating* listing, not the one on screen. Location-hierarchy restrictions vary by feature (see Section F). KSA and EGY code is merged into the same codebase — a standing regression risk (see Section F).

---

## D. Key flows and surfaces

| Surface | Team term | Entry points |
| --- | --- | --- |
| Listing detail | DPV | Deeplink, remarketing, LPV, MapView, Gallery View, Saved Searches, Activity Log, Agent/Agency DPV, Blogs, Push |
| Search results | LPV | Home search, Popular, Lookup Nearby, Previously Applied sheet, Saved Searches, CBS, DT rail, Agent/Agency DPV, Activity Log, Blogs, Manage Alerts, Deeplinks, Push |
| Commute search | CBS / Search 2.0 | Home banner, Filters screen banner/toggle |
| Dubai Transactions | DT | Home header, Home banner, LPV inline rail (position 10), More screen, deeplink |
| Image gallery | Gallery View | Opened from DPV (Portrait + Landscape on iPhone) |
| Map search | MapView | Search, filter toggle |
| Promotional widget carousel | Homepage banners | Top of homepage, above the Home carousels (TruEstimate, Portfolio, Dubai Transactions, Propco, TruBroker, etc.) |

**LPV inline widget positions (fixed, business-critical):** TruBroker = after 1st listing, BayutGPT = after 3rd, TruEstimate = after 7th, Dubai Transactions = after 10th. Only widgets with data render.

**Deeplinks:** domain `bayut.com`; localised prefixes `/ar/`, `/zh/`, `/ru/`. Test in fresh-install, killed, and background states. **MoEngage** drives recommended/remarketing links and push. **Adjust** drives deferred deeplinks — after install+onboarding the user must land on the deep-linked screen, and Adjust must record LPV/DPV/Unique-Lead events (iOS requires the ATT prompt to be allowed).

**Separated trigger/effect flows (bug-prone):** a lead on the DPV/Gallery View can trigger a nudge shown later on a different DPV or after relaunch. Purpose must be read from persisted state, not the current screen.

---

## E. Regression-critical areas

*Distilled from the Bayut UAE regression checklist. Protect these when a feature touches nearby code.*

- **Leads from every surface** — Email/Phone/SMS/WhatsApp must work from LPV, DPV, Gallery View, deeplinks, remarketing, Favourites, Activity Log, Agent/Agency LPV+DPV, Area Prime Slot, TruBroker Story, Project CPL. This is the primary conversion; leakage here is severe.
- **App state retention on override** — logged-out and logged-in (Consumer and Agent) must retain Favourites, Recent/Last Search, Saved Searches, Alerts, BayutGPT history, Activity Log. Test on shared Regression/Hotfix Production builds.
- **Sign In / Sign Up matrix** — Email, Google, Facebook, WhatsApp, One-Time-Link, Apple (iOS); plus Forgot Password and Implicit Register ("Alert Me of New Properties"); from many entry points (More, Manage Alerts, Saved Searches, BayutGPT, TruEstimate).
- **DPV against Web, especially DLD data** — Dubai Land Department sections (Validated/Building/Project Information, Regulatory Info, Trakheesi Permit QR) are explicitly "must not be missed". Verify regulatory fields (Trakheesi, RERA, BRN, Madhmoun, ADM, etc.) against Web.
- **Location-hierarchy restrictions per feature** — each feature allows a different loc-level depth (see Section F); a change to location handling can silently break one of ~17 rules.
- **Filters and slotting across surfaces** — Filters screen, Quick Filters bar, LPV inline filters, Previously Applied sheet; Beds/Baths must be hidden for Commercial types.
- **Delete Account** — must fully block re-login ("No account associated"); Apple rejects builds where this fails, so verify on iPhone **and iPad**. Behaviour varies by role (Agent, Agency Owner, Admin).
- **Dubai Transactions (incl. Claim & Share Transactions)** — data parity with Web, claim/admin-claim state machine (Claimable → Pending → Rejected/Approved), agent eligibility rules, 30-transaction share cap, PDF export.
- **TruEstimate (Standard / Branded / Portfolio / Alerts)** — sale vs rental report differences, agent vs end-user locked-report flow, branded-report email matching, portfolio metrics.
- **Firebase Crashlytics** — review fatal and non-fatal before sign-off; do not approve on manual passes alone.

---

## F. App-specific edge cases and gotchas

- **The rating/App-Review bottom sheet is a shared shell.** Multiple nudges reuse it (App Review triggers on 3+ Favourites in a session, a TruEstimate report, or viewing 5 DT transaction details). Any feature built on that shell needs a regression case confirming the other nudges are unchanged.
- **Purpose is read from persisted state, not the current screen.** A lead on a Sale DPV reports `purpose = Sale` even when a deferred surface renders on a Rent DPV. Test both directions.
- **KSA/EGY code is merged in.** Logos, lead templates, and Contact Us content must show **no EGY or KSA text** on Bayut UAE — an explicit regression check because the codebases are shared.
- **Location-level restrictions differ by feature** (from the checklist): LPV/Projects — no restriction; DT — Dubai + children only; Seller Leads — L3+; Search 2.0 — L1+; Find My Agent — L2/L3 depending on section; TruEstimate unit search — L2/L3 under Dubai. A feature touching location must re-verify its own rule.
- **Area Prime Slot** is business-critical, has a distinct fat card, appears in L3+ locations (Business Bay, Downtown, JVC), and has **no badge on the app** — verify via Web.
- **Widget visibility conditions** — TruBroker widget: L3+ in Dubai/Abu Dhabi only, hidden at emirate/UAE level and when multiple locations are selected. Off-Plan rails: Buy purpose + All/Ready completion. Each widget has its own condition.
- **Integrations:** MoEngage (push, remarketing), Adjust (deferred deeplinks, ATT-gated on iOS), PRYPCO (mortgage/pre-approval web-views), Algolia (search count differs slightly from Web due to background sync — a known non-bug), Zero Bounce (email-lead validation delays leads on Profolio by 30 min–3 hr — a known non-bug).
- **Historical leakage:** TODO — add categories as defects escape to production.

---

## G. App-specific learnings

*App-scoped rules only; group-wide rules live in `../learnings.md`.*

## UAE-001 — "Homepage banners", not "promotional banner carousel"
**Date:** 2026-08-13
**Captured from:** Review of the Recently Viewed Properties suite (Mustafa)
**Rule:** Refer to the rotating promotional widget at the top of the Bayut UAE homepage as "Homepage banners" — never "promotional banner carousel". It surfaces TruEstimate, Portfolio, Dubai Transactions, Propco, TruBroker and other entry points; see Section B/D.
**Why:** The QA team's own vocabulary is "Homepage banners" — an invented term drifts from how the team actually talks about the surface, the same failure mode `context/checklist-corrections.md` documents for the sister automation project's SRP/LDP-vs-LPV/DPV mixup.
**Example:** Not "the section is rendered directly below the homepage promotional banner carousel" but "...directly below the Homepage banners carousel".

## UAE-002 — `recently_viewed_carousel_homepage` confirmed Remote Config contract
**Date:** 2026-08-16
**Captured from:** QA lead, direct spec confirmation during Recently Viewed Properties Testmo review (Mustafa)
**Rule:** The Remote Config key `recently_viewed_carousel_homepage` has three defined values, each with a confirmed effect:
| Value | Home screen | Activity Log (More screen) |
| --- | --- | --- |
| `recently_viewed_control` | Recently Viewed Properties section **not shown** | Viewed Properties section **shown** |
| `recently_viewed_variant` | Recently Viewed Properties section **shown** | Viewed Properties section **shown** |
| `null` | Recently Viewed Properties section **not shown** | Viewed Properties section **shown** |

`null` and `recently_viewed_control` are behaviourally identical on both surfaces — `null` is not a distinct third UI state, just an unresolved-config case that degrades to the same behaviour as `control`.
**Why:** Removes ambiguity from every Recently Viewed case's `Given`/`Then` clauses for this key — no case needs to hedge on what `null` does anymore.
**Note:** This confirms the *visibility* contract per bucket. It does **not** resolve the separate, still-open question of how many properties a user must view before the Home section activates (the "1 view vs 3 views" contradiction tracked in `test-cases/recently-viewed-properties/modified-cases.md`) — that's an activation threshold, not a bucket-visibility rule, and remains unconfirmed.

## UAE-003 — Recently Viewed / Activity Log history is device-local storage, not account-synced
**Date:** 2026-08-16
**Captured from:** QA lead, direct confirmation during Recently Viewed Properties Testmo review (Mustafa)
**Rule:** Viewing history (Home carousel + Activity Log "Viewed Properties") is stored in the app's local storage on-device, not synced server-side to the account.
**Why:** Explains and ties together the retention behavior across several cases in this suite: survives an override install (§3 of the regression checklist — local storage isn't touched by an override) and survives an account switch on the same device (case 47 — the history belongs to the device, not the signed-in account), but is wiped by a full uninstall/reinstall (case 46 — uninstall clears local storage).
**Caution:** Don't assume this generalises to *other* local data (Favourites, Saved Searches, etc.) without separate confirmation — this fact is specifically about viewing history, not a blanket statement about everything the app stores locally.
