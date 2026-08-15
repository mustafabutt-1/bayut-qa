# Dubizzle Egypt

**Status:** Complete — populated from the Dubizzle Egypt regression checklist.
**Platforms:** iOS, Android (native)
**Testmo project ID:** 40 (site: dubizzlelabs.testmo.net)

Classifieds, not property — vocabulary and flows differ sharply from the Bayut apps. The defining complexity of this app is its **seller-role matrix**: Normal user, Guest, and several Agency/Agent types, each with different dashboards, posting rules, and upsell screens.

---

## A. Configuration

| Setting | Value |
| --- | --- |
| Testmo project ID | **40** |
| Features repo | `/repositories/40?group_id=79017` — create a new folder per feature under group **79017** |
| Case template | TODO |
| Primary market(s) | Egypt |
| Bundle IDs (iOS / Android) | TODO |

### Languages

| Code | Language | RTL | Notes |
| --- | --- | --- | --- |
| EN | English | No | Locale formatting: EGP currency, DD/MM/YYYY dates |
| AR | Arabic | **Yes** | **Primary language.** RTL must be pixel-perfect, especially on Post Ad form, Upsell, Dashboard tables, and Lead cards |

Localisation must cover error/validation/system messages too (Low Credits, Package Exhausted, OTP prompts, moderation rejection reasons). Language toggle must work without app restart. **Light and Dark mode** both apply. No AR strings may bleed into EN mode and vice versa.

### Device matrix

| Platform | Devices |
| --- | --- |
| iOS | iPhone (latest + older OS), **iPad** (Portrait + Landscape smoke) |
| Android | Phone (latest + older OS) |

*(Confirm whether a foldable is in the Dubizzle Egypt device pool — the checklist did not name one.)*

### Minimum supported OS

TODO — confirm iOS and Android floors.

### Analytics

Platform: Firebase (GA4) + MoEngage for push. Deeplinks doc referenced as "Dubizzle EG Deeplinks". Search events tracked via Firebase.

Recurring checks: LPV (`search_result_impression`, `page_view`), DPV (`page_view`), leads by channel, MoEngage push (Sent/Received/Clicked/Dismissed) in **killed and background**. **Guest Post Ad** additionally requires MoEngage funnel events (form submit, OTP verify, package select, payment success) and **GA session ID stored with the draft** for marketing attribution.

### Remote config

Platform: TODO. Many behaviours are backend/business-plan driven rather than simple flags: category availability per user type, free-posting limits per category, package/credit rules, Elite eligibility.

---

## B. Vocabulary

| Term | Meaning |
| --- | --- |
| Ad / listing | A classified post (not a "property"/DPV in the Bayut sense) |
| LPV | Listing page view — search results |
| DPV | Detail page view of a single ad; **My DPV** = the owner's view of their own ad |
| Post Ad | The ad-creation flow |
| Upsell | Post-submission screen offering promotion/packages, **different per user type** |
| Elite / Featured / Auto Refresh | Promotion tiers |
| Car of the Week / Property of the Week (POW) | Rotating premium placements, category-specific |
| Credit user vs Package user | Two agency billing models, each with distinct dashboard/upsell |
| Pro Dashboard | Agency/Agent management dashboard (Normal users must never see it) |
| Pro Lite | Single-operator agency (credits, no sub-agents) |
| Hotline | 4-digit agency call number shown on some ads |

---

## C. Product domain

- **Vertical:** General classifieds — Motors, Property, Jobs, Electronics/Mobiles, Laptops, Home, and more. Three top-level tabs: **Home, Motors, Property**.
- **Core value exchange:** a **lead** — Phone (dialer or 4-digit hotline), Chat (in-app), or WhatsApp. Jobs use **Quick Apply**. Logged-out users hit a login gate on Call/Chat/WhatsApp.
- **Who posts and who consumes:** a rich seller matrix — **Normal user, Guest (unauthenticated), Credit Agency, Credit Agent, Package Agency, Package Agent, Pro Lite (credits)**. Each has different visible categories, posting limits, dashboards, upsell screens, and role restrictions. This is the single biggest test dimension in the app.
- **Structurally notable:** card type is category-driven (Property, Cars for Sale, Jobs → fat cards; others → lean cards). Ad lifecycle (Active/Pending/Rejected/Inactive/Sold/Deleted) governs whether leads can be received. **Hatla2ee cross-posting** is a Cars-only capability for eligible agencies.

---

## D. Key flows and surfaces

| Surface | Team term | Entry points |
| --- | --- | --- |
| Search results | LPV | Home search bar, Filters, Motors/Property landing, Saved/Recent searches, "Explore more categories", Hero categories, Deeplinks |
| Ad detail | DPV / My DPV | Home hero categories, Motors/Property landing rails, Favourites, Chats inbox, Public Profile, Applied Jobs, Deeplinks |
| Ad creation | Post Ad | Bottom-nav Post Ad, Home CTA, My Ads CTA |
| Seller management | Pro Dashboard | Agency/Agent login (never Normal users) |
| Promotion | Upsell | After Post Now, "Sell Faster Now", Edit & Post/Republish at limit |

**Bottom nav:** Home, Chats, Sell, My Ads, Account.

**LPV slotting (business-critical, category-dependent):** fixed page size 45. Property = 10 Elite + 20 Featured + 15 Normal (Featured **not** randomized for Property; slotting **retained** after sort). Other categories = 5 Elite (randomized) + 40 Featured (randomized), fallback fills with Normal. Sort options change slotting: Most Relevant keeps it; Newly Listed / Verified-First bypass it. Google Ads after listing 2 then 8; post-ad banner after 7; full-screen ad after 14.

**Location:** Egypt hierarchy L0 Egypt → L1 (e.g. New Cairo) → L2 → L3. Nearby-results fallback logic is location-level dependent.

---

## E. Regression-critical areas

*Distilled from the checklist. Protect these when a feature touches nearby code.*

- **The seller-role matrix.** Every posting, dashboard, upsell, and permission behaviour must be verified per user type: Normal, Guest, Credit Agency, Credit Agent, Package Agency, Package Agent, Pro Lite. **Cross-contamination between types must never occur** (an agent must never see the agency owner's other ads; a Normal user must never see the Pro Dashboard).
- **Role-based restrictions must be enforced, not just hidden.** Agents cannot purchase credits/packages, manage other agents, or view agency-wide analytics — test by direct navigation where possible, not just UI absence.
- **Guest Post Ad ("progress first, identity later").** Login must not gate the initial flow; OTP fires on Post Now, before package/payment; account-resolution must never create duplicate accounts; guest posts get the same moderation as authenticated ones.
- **Upsell correctness per type.** Credit vs Package vs Normal upsell differ in UI and logic; Elite/Featured mutual exclusivity; Low Credits disables the right package and the Post CTA; agent upsell shows "Contact Agency Owner".
- **Credit and package accounting.** Posting deducts the right amount for the right duration; balances never go negative; agency→agent credit/quota assignment reflects correctly on both sides; usage history logs.
- **Ad lifecycle and leads.** Leads must **not** be deliverable on Inactive/Rejected/Pending/Deleted ads. Lifecycle actions (Edit → possible re-moderation, Republish consumes quota, Mark as Sold, Deactivate, Delete) must update buyer-facing search correctly.
- **Lead attribution.** Agency-owned ad leads appear in both the Agency Leads section and the assigned agent's Leads. Lead counts match across channel tabs.
- **Hatla2ee cross-posting** (see Section F).
- **Payments** — Fawry, card, mobile wallets, Valu; success and failure paths.
- **Localisation** — Arabic RTL pixel-perfection on seller screens; localised error/validation messages.
- **Firebase Crashlytics** — fatal and non-fatal reviewed before sign-off, with attention to seller flows.

---

## F. App-specific edge cases and gotchas

- **Hatla2ee integration (Cars-only).** Hatla2ee Phone/WhatsApp fields appear **only** in Cars for Sale Post Ad for eligible agencies, labelled Optional. Entering a Hatla2ee number cross-posts the ad to the Hatla2ee platform (verify branding on both apps); leaving it blank must not block submission. The underlying credit/package billing model is unchanged by Hatla2ee. Fields must **never** appear for Normal users, non-Hatla2ee agencies, or non-Cars categories. *(Hatla2ee is also its own standalone app — see `hatla2ee.md`.)*
- **My DPV vs DPV.** An owner viewing their own ad sees My DPV, not the standard buyer DPV — an easy miss.
- **Card type is category-driven.** Property/Cars/Jobs = fat cards; everything else = lean cards. Featured Business rail shows only for categories with agencies and is randomized per LPV reload (except Property).
- **Guest draft rules.** Max 1 concurrent guest draft per session; draft auto-saves locally; GA session ID must persist with the draft for attribution.
- **Web-only features.** Package quota assignment to agents is web-only; the app must reflect the assigned quota but cannot set it.
- **Checklist location example uses Pakistan locations** (Gulberg/Lahore) to illustrate nearby-fallback levels — that is illustrative of the *logic*, not Egypt data. Use Egypt locations (New Cairo hierarchy) when writing actual cases.
- **Integrations:** MoEngage (push + guest funnel), Firebase/GA4, payment gateways (Fawry, Valu, wallets), Hatla2ee platform.
- **Historical leakage:** TODO — add as defects escape to production.

---

## G. App-specific learnings

*App-scoped rules only; group-wide rules live in `../learnings.md`.*

*(none yet — captured via the `update-knowledge` skill)*
