# Zameen PK

**Status:** Complete — populated from the Zameen regression checklist.
**Platforms:** iOS (iPhone, iPad, Mac M1+, Apple Vision), Android (Phone, Fold)
**Testmo project ID:** TODO

Pakistan property marketplace — same family as Bayut, but with its own vocabulary, Pakistani area units, Urdu RTL, and a self-serve seller flow (Add Property, quota/credits, paid promotions).

---

## A. Configuration

| Setting | Value |
| --- | --- |
| Testmo project ID | TODO |
| Case template | TODO |
| Primary market(s) | Pakistan |
| Bundle IDs (iOS / Android) | TODO |
| Web parity source | zameen.com |
| Lead destination | profolio.zameen.com |

### Languages

| Code | Language | RTL | Notes |
| --- | --- | --- | --- |
| EN | English | No | Default |
| UR | Urdu | **Yes** | **RTL — same layout rigor as Arabic on the Bayut apps.** Watch numeric fields (price, area), date/time, and mixed Latin/Urdu strings. Also test mixed locale (app Urdu + device English and vice versa) |

Only EN + UR are supported (per store listings). **Translation sheets are not provided by product** — verify against the app and Web. Currency switchable (PKR primary; USD, CAD, GBP, AED, SAR) — verify conversions on LPV/DPV/Add Property. **Area Unit** switchable (Marla, Kanal, Sq Ft, Sq M, Sq Yards) — verify on LPV, DPV, Add Property, Filters, Plot Finder. Some cities fix a default unit (e.g. Karachi → sq. yd.).

### Device matrix

| Platform | Devices |
| --- | --- |
| iOS | iPhone (latest + older OS), **iPad** (Portrait + Landscape), **Mac M1+** ("Designed for iPad" build), **Apple Vision** (visionOS 1.0+, if in release scope) |
| Android | Phone (latest + older OS), **Fold** (folded, unfolded, transition with state continuation), **low-end (Android 7/8)** — critical, as Pakistani device landscape skews lower-spec |

### Minimum supported OS

Per checklist: **iOS 26, 18, 17, 16, 15**; **Android 16, 14, 10, 8/7**. Confirm each cycle.

### Analytics

Platform: Firebase (GA4) + MoEngage for push. Events sheet: [Zameen - Events Tracking](https://docs.google.com/spreadsheets/d/1ApZIlTXhx0XcLB_AfZKuVZRaO6f5Lk9Uo7vNMiTr084/edit). Leads land on profolio.zameen.com.

Recurring checks: leads (`email_lead`, `phone_lead`, `sms_lead`, `whatsapp_lead`), LPV, DPV, Post Ad, Quota/Credits, Zameen Shop (success/failure), MoEngage push (Sent/Received/Clicked/Dismissed) in **killed and background**. WhatsApp/SMS **TraceID must match `event_unique_id`**. Email leads may take 30 min–3 hr via Zero Bounce (known non-bug). Payment flows use Checkout.com test cards on staging.

### Remote config

Platform: TODO. Rating popup threshold is session/event driven. Confirm flag conventions.

---

## B. Vocabulary

| Term | Meaning |
| --- | --- |
| LPV | Listing page view — search results |
| DPV | Property detail view |
| Add Property / Post Ad | The listing-creation flow |
| My Properties | Seller's own listings (Active/Pending/Rejected/Expired/Deleted/Downgraded/Not Active) |
| Plot Finder | Interactive society/plot map tool with plot polygons and a saved collection |
| Story Ads | Short story-format promoted ads in an LPV inline rail |
| Super Hot / Hot / Refresh | Paid promotion tiers (credits-based) |
| Titanium+ | A top-priority listing tier surfaced first on LPV |
| Quota / Credits | Listing quota + credit balance for paid actions |
| MyZameen | Separate investment app — Invest CTA/banner deep-links to its store page |
| CPML | Cost Per Lead / re-targeting flow via MoEngage |
| Marla / Kanal | Pakistani area units |

---

## C. Product domain

- **Vertical:** Residential and commercial property (Buy/Rent/Invest), Plots, and New Projects.
- **Core value exchange:** a **lead** — Email, Phone, SMS, WhatsApp — verified on profolio.zameen.com. Leads fire from LPV cards, DPV (sticky bottom + Gallery + single-image view), Favourites, Story Ads, New Project DPV.
- **Who posts and who consumes:** self-serve sellers post via **Add Property** (with profile tags: premium / basic / agent); buyers browse and generate leads. Unlike Dubizzle's heavy agency-dashboard matrix, Zameen's seller flow is individual, governed by **quota and credits** rather than agency roles.
- **Structurally notable:** **Plot Finder** is a Zameen-distinctive map tool (plot polygons, saveable collections). Pakistani **area units** (Marla/Kanal) and per-city default units are pervasive. **MyZameen** invest CTA leaves the app to a separate product.

---

## D. Key flows and surfaces

| Surface | Team term | Entry points |
| --- | --- | --- |
| Search results | LPV | Home search, Side Menu search, Bottom-nav Search, Saved/Recent searches, Deeplinks, Push |
| Property detail | DPV | LPV, Search by Property ID (direct), Recommended rail, Deeplinks, Push |
| Listing creation | Add Property | Home card CTA, Side Menu, Profile, My Properties, Drafts |
| Plot map tool | Plot Finder | Home banner, Side Menu, Property DPV |
| Promoted stories | Story Ads | LPV inline rail |

**Bottom nav:** Home, Projects, Search, Favourites, Profile. Navigation is **Side Menu / More**-driven (not a Bayut-style More tab).

**Deeplinks doc:** [Zameen deeplinks](https://docs.google.com/document/d/1WXctx4dqhyfgFxtkqXZTSNWR_nY4gVWteSL4aga1E3I/edit). Cover Property DPV, LPV-with-filters, New Project DPV, Agent/Agency profile, Plot Finder, Favourites/Saved Search — in killed and background states; query params (location, type, purpose, filters) must be retained.

---

## E. Regression-critical areas

*Distilled from the checklist. Protect these when a feature touches nearby code.*

- **Session persistence.** User must stay logged in across app close, override, device restart, and 7+ days idle. **Explicitly high-priority** — an auto-logout bug was surfaced in Play Store reviews.
- **Leads from every surface**, verified on profolio.zameen.com; TraceID↔`event_unique_id` match for WhatsApp/SMS.
- **Add Property end-to-end.** Full field set incl. area+unit, price checker (activates only after location confirmed on map), installments, images (up to 50, primary selection, reorder, delete). Validation must give **field-specific** messages, never a generic "data given is invalid" (a called-out recurring bug).
- **Edit Property.** Pre-populates with current values; edits and image add/remove persist after save; no spurious "data invalid" error.
- **Drafts.** Save mid-flow (incl. backgrounding during image upload); persist across close/override/restart; upload directly from a draft.
- **Quota & Credits.** Correct display and consumption; confirmation before deduction; balance never negative; clear insufficient-quota messaging with a purchase CTA.
- **Paid promotions** (Super Hot / Hot / Refresh / Story / Verified Photography+Videography) — confirmation, correct credit cost, instant listing-state and badge update.
- **App state retention on override** — logged-out (Recent Searches, Viewed) and logged-in (+ Saved Searches, Favourites, Drafts, My Properties).
- **Location & area units** — multi-location (max 5); Beds/Baths hidden for Commercial sub-types; per-city default area unit; currency/area-unit switches app-wide.
- **DPV against Web** (zameen.com) — no data missed; Gallery in Portrait + Landscape on iPad/Fold.
- **Swipe-back gesture** — flagged as a **recurring regression** across the app, Side Menu especially.
- **Firebase Crashlytics + ANRs/Hangs** — extra attention this cycle given Play Store reviews citing crashes; watch low-end Android.

---

## F. App-specific edge cases and gotchas

- **Urdu RTL is a first-class layout test.** Numeric fields (price, area), date/time, and mixed Latin/Urdu strings are the usual break points; also test mixed locale (app language ≠ device language).
- **Price checker gating.** It activates only once location is confirmed on the map — a common source of "why isn't it updating" confusion.
- **Generic validation error is a known bug class.** Any Add/Edit Property change should assert field-specific validation, explicitly not "data given is invalid".
- **Delete Account keeps the token ~1 month** — the user can still log in during that window (documented behaviour, not a bug). Contrast Bayut UAE, where re-login must fail immediately. Do not copy Bayut's Delete Account expectation here.
- **Plot Finder** — society picker, satellite/default toggle, plot polygons, collection save/rename/share, navigate-to-maps, and graceful tile loading on poor network. Returning from Plot Finder must not break the nav stack.
- **MyZameen Invest** CTA/banner deep-links **out** to the MyZameen app's store page — not an in-app screen.
- **Excluded locations** block Saved Search registration.
- **Android favourite undo** — deleting a favourite offers an Undo (Android); logged-out favourites merge on login.
- **Integrations:** MoEngage (push + CPML re-targeting), Firebase/GA4, Algolia/internal search (count differs slightly from Web — flag only >5%), Checkout.com (payments, test cards), Zero Bounce (email-lead delay).
- **Historical leakage:** auto-logout and app crashes (both surfaced in recent Play Store reviews); swipe-back regressions. Add more as they arise.

---

## G. App-specific learnings

*App-scoped rules only; group-wide rules live in `../learnings.md`.*

*(none yet — captured via the `update-knowledge` skill)*
