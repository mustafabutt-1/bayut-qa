# Screen Inventory — Bayut UAE Android App

One row per screen. `locator-cartographer` **owns this file after Phase 3** — it appends
verified data from real page-source dumps and replaces `[ASSUMED — verify]` rows with
evidenced ones. Until then this is a hypothesis, not a map.

**Package name:** `TODO` — get from `adb shell pm list packages | grep bayut`. Store as
`BAYUT_APP_PACKAGE` in `.env`.
**Main activity:** `TODO` — get from `adb shell dumpsys window | grep mCurrentFocus`.

---

## Column meaning

- **Screen ID** — stable slug; screen-object class and file name derive from it.
- **Entry points** — how a test can *arrive*. Deep link beats UI navigation every time.
- **Deep link** — `TODO` until verified with `adb shell am start -a android.intent.action.VIEW -d "<url>"`.
- **Key elements** — what a test asserts on. Filled from real page source, not guessed.
- **ID quality** — `GOOD` (stable accessibility id / resource-id) / `PARTIAL` / `NONE`
  (XPath required). Every `NONE` becomes a line item in `docs/ASKS.md`.

---

## Core flow

| Screen ID | Name | Entry points | Deep link | Key elements | ID quality |
|---|---|---|---|---|---|
| `splash` | Splash / cold start | app launch | n/a | — | TODO |
| `onboarding` | First-run onboarding | fresh install | n/a | skip, next, permission prompts | TODO |
| `home` | Home / discover | launch, tab bar | `TODO` | purpose toggle, search entry, recommended rail | TODO |
| `search_entry` | Search location input | home search bar | `TODO` | location autocomplete field, suggestion list, recent searches | TODO |
| `search_results_list` | Results — list view | search submit, deep link | `TODO` | result count header, listing cards, filter chips row, sort control, pagination sentinel | TODO |
| `search_results_map` | Results — map view | toggle from list | `TODO` | map, pin clusters, draw-area control, bottom card carousel | TODO |
| `filters` | Filter sheet / screen | filter button | `TODO` | every control in `filter-inventory.md`, "Show N properties", reset | TODO |
| `listing_detail` | Listing detail (LDP) | card tap, deep link, share link, push | `TODO` | gallery, price, beds/baths/area, TruCheck badge, description, amenities, agent card, contact bar | TODO |
| `gallery` | Photo gallery / fullscreen | LDP image tap | n/a | pager, counter, close, floor-plan / 360 tabs | TODO |
| `contact_agent_sheet` | Contact options | LDP contact bar | n/a | Call, WhatsApp, Email buttons | TODO |
| `enquiry_form` | Email enquiry form | contact sheet | n/a | name, email, phone, message, submit, validation errors, success state | TODO |

## Account and retention

| Screen ID | Name | Entry points | Deep link | Key elements | ID quality |
|---|---|---|---|---|---|
| `login` | Login / signup | profile tab, gated action | `TODO` | email, password, social buttons, OTP entry, error banner | TODO |
| `favourites` | Saved properties | tab bar | `TODO` | saved list, empty state, remove action | TODO |
| `saved_searches` | Saved searches + alerts | tab bar / profile | `TODO` | saved search rows, alert toggle, delete | TODO |
| `profile` | Profile & settings | tab bar | `TODO` | language, currency, area unit, notification prefs, logout | TODO |
| `notifications` | Notification centre | bell icon | `TODO` | list, empty state | TODO |

## Secondary

| Screen ID | Name | Entry points | Deep link | Key elements | ID quality |
|---|---|---|---|---|---|
| `agency_profile` | Agency page | LDP agent card | `TODO` | agency listings, contact | TODO |
| `agent_profile` | Agent page | LDP agent card | `TODO` | agent listings, contact | TODO |
| `new_projects` | New projects / off-plan | home, tab | `TODO` | project cards, project detail, register-interest form | TODO |
| `mortgage_calculator` | Mortgage calculator | LDP, tools | `TODO` | price, down payment, rate, tenure, monthly output | TODO |
| `area_guide` | Area guide / insights | search suggestions, LDP | `TODO` | likely webview `[ASSUMED — verify]` | TODO |
| `floor_plan` | Floor plans | LDP | n/a | plan viewer, unit selector | TODO |
| `tour_360` | 360 / video tour | LDP | n/a | player, likely webview `[ASSUMED — verify]` | TODO |

## System / cross-cutting states (not screens, but must be inventoried)

| State ID | Trigger | What must be visible |
|---|---|---|
| `state_offline` | airplane mode / no network | offline message + retry, never a blank list |
| `state_error_5xx` | mitmproxy fault injection | error message + retry, never a silent empty state |
| `state_empty_results` | over-constrained filter | explicit empty state + route out |
| `state_loading` | any fetch | skeleton or spinner, bounded — never indefinite |
| `state_permission_denied` | location denied | graceful degrade, no crash, no dead-end |
| `state_session_expired` | token expiry | re-auth prompt, action preserved after re-auth |

---

## How to populate this properly (Phase 3, `locator-cartographer`)

1. `python tools/adb.py devices` → confirm one device.
2. `python tools/adb.py reset-app --package $BAYUT_APP_PACKAGE`.
3. Drive to each screen; dump page source per screen to
   `context/page_source/<screen_id>.xml`.
4. For each screen, extract every interactive element and record:
   `accessibility id` / `resource-id` / text / class / bounds.
5. Set **ID quality**; every `NONE` element goes into
   `reports/missing-testids.md` with a screenshot and a proposed identifier name.
6. Re-dump in `ar` locale. Elements whose only identifier is *text* break under Arabic —
   flag them separately; they are the highest-priority testID asks.

## Known unknowns

- `UNKNOWN — needs manual verification`: which screens are native vs webview. Webviews
  need `context.switch_to` and Chromedriver — a materially different test approach.
- `UNKNOWN — needs manual verification`: whether the app registers HTTP App Links, custom
  scheme (`bayut://`), or both. Determines the entire test-setup strategy.
- `UNKNOWN — needs manual verification`: whether deep links bypass onboarding on a fresh
  install. If not, every test pays the onboarding cost.
