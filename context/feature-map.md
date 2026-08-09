# Feature Map — Bayut UAE Android App

Ground truth for every agent that needs to know *what the app does* and *what matters*.
`regression-scoper`, `suite-curator`, and `test-designer` all read this file. If it is
wrong, their output is wrong.

**Status:** first draft, populated by inference from the public Bayut UAE product.
Everything marked `[ASSUMED — verify]` is a guess. Correct it before Phase 1.

**Legend**
- **Risk** — H / M / L. Blast radius × change frequency × revenue proximity.
- **Cases** — count of existing manual cases in Testmo for this area. `TODO` = not yet
  reconciled against the 144.
- **Lead flow?** — does a defect here directly block an agent lead (our revenue event)?

---

## Tier 1 — Revenue path (a defect here loses money the same day)

| # | Feature area | Risk | Cases | Lead flow? | Notes |
|---|---|---|---|---|---|
| 1 | Search — purpose toggle (Buy / Rent) | H | TODO | Indirect | Root of every session. `[ASSUMED — verify]` also Commercial + New Projects tabs |
| 2 | Search — location autocomplete & multi-location | H | TODO | Indirect | Emirate → area → community → tower/sub-community hierarchy `[ASSUMED — verify]` |
| 3 | Search results list (pagination / infinite scroll) | H | TODO | Indirect | **API-oracle target #1** — server returns N, client must render N |
| 4 | Filters (see `filter-inventory.md`) | H | TODO | Indirect | Largest combinatorial surface in the app |
| 5 | Listing detail page (LDP) | H | TODO | Yes | Gallery, price, specs, description, amenities, agent card |
| 6 | Contact agent — Call | H | TODO | **Yes** | Dialer intent + lead POST. `[ASSUMED — verify]` |
| 7 | Contact agent — WhatsApp | H | TODO | **Yes** | External app handoff; prefilled message `[ASSUMED — verify]` |
| 8 | Contact agent — Email / enquiry form | H | TODO | **Yes** | Validation, success state, duplicate-submit guard |
| 9 | Map search / draw-on-map | H | TODO | Indirect | Pin clustering, viewport-bound results `[ASSUMED — verify]` |

## Tier 2 — Retention and trust

| # | Feature area | Risk | Cases | Lead flow? | Notes |
|---|---|---|---|---|---|
| 10 | Saved searches + alerts | M | TODO | Indirect | Push notification delivery is partly out of our control |
| 11 | Favourites / shortlist | M | TODO | No | Sync across login state `[ASSUMED — verify]` |
| 12 | Login / signup (email, social, OTP) | H | TODO | Indirect | Blocks favourites, saved searches, and lead attribution |
| 13 | User profile & settings | L | TODO | No | Locale, currency, area unit, notification prefs |
| 14 | TruCheck™ verified badge & filter | M | TODO | Indirect | Trust marker — a wrong badge is a credibility defect `[ASSUMED — verify]` |
| 15 | Agency / agent profile pages | M | TODO | **Yes** | Agent listing counts, contact from profile |
| 16 | Recently viewed / search history | L | TODO | No | `[ASSUMED — verify]` |
| 17 | Share listing (deep link out + in) | M | TODO | Indirect | Inbound deep links are our fastest test-setup path |

## Tier 3 — Content, tools, discovery

| # | Feature area | Risk | Cases | Lead flow? | Notes |
|---|---|---|---|---|---|
| 18 | New Projects / off-plan section | M | TODO | Yes | Separate lead form `[ASSUMED — verify]` |
| 19 | Mortgage calculator | L | TODO | No | Pure client math — cheap, high-certainty oracle |
| 20 | TruEstimate™ / property valuation | M | TODO | Indirect | `[ASSUMED — verify]` availability in app |
| 21 | Bayut Insights / market trends & area guides | L | TODO | No | Mostly webview `[ASSUMED — verify]` |
| 22 | Floor plans | L | TODO | No | `[ASSUMED — verify]` |
| 23 | 360° tours / video tours | M | TODO | No | Webview or player; a common crash source |
| 24 | Commercial vertical (Buy / Rent) | M | TODO | Yes | Different property types and filter set |
| 25 | Currency switcher (AED / USD / …) | M | TODO | No | Price formatting regressions cascade everywhere |
| 26 | Area unit switcher (sqft / sqm) | M | TODO | No | Same — a formatting bug looks like a data bug |

## Tier 4 — Cross-cutting (test *through* every area above, not as its own tab)

| # | Concern | Risk | Cases | Notes |
|---|---|---|---|---|
| 27 | Arabic locale + RTL layout | H | TODO | Mirroring, numerals, truncation, alignment. Own pytest marker: `arabic` |
| 28 | Offline / flaky network / airplane mode | H | TODO | Empty vs error vs stale-cache states are routinely conflated |
| 29 | Empty states & zero-result searches | M | TODO | Filter combos that legitimately return nothing |
| 30 | Error states & retry affordances | H | TODO | 4xx/5xx/timeout — inject via mitmproxy, not by waiting for luck |
| 31 | Push notifications (deep-link landing) | M | TODO | Cold start vs warm start divergence |
| 32 | App upgrade / migration from prior version | H | TODO | Session, favourites, and saved-search survival across upgrade |
| 33 | Permissions (location, notifications, storage) | M | TODO | Denied / "only this time" / revoked-while-backgrounded |
| 34 | Deep links & App Links (inbound) | M | TODO | Also our primary test-setup mechanism — a break here breaks the suite |
| 35 | Accessibility (TalkBack, font scaling, contrast) | M | TODO | Ties directly to the testID ask in `docs/ASKS.md` |
| 36 | Performance (cold start, scroll jank, image load) | M | TODO | Measure, don't assert, until we have baselines |

---

## Reconciliation TODO — the 144 cases

`suite-curator` cannot do its job until this table is real. Before Phase 3:

- [ ] Export all 144 Testmo cases with their suite/section assignment.
- [ ] Map each case to exactly one feature-area number above.
- [ ] Fill the `Cases` column; flag any area with **0 cases** as a coverage gap.
- [ ] Flag any case that maps to **no** area — either the area is missing here or the
      case is stale.
- [ ] Record areas with the highest defect density from ClickUp history (drives
      `regression-scoper` risk weighting). Needs a ClickUp export — see `docs/ASKS.md`.

## Fields to add once known (do not invent)

- **Owner (dev squad)** per area — needed so bug reports route correctly.
- **Change frequency** — release notes over the last 6 releases. Highest-churn areas get
  the heaviest regression weight.
- **Historical defect density** — defects per area per release from ClickUp.
- **Feature-flag coverage** — any area behind a remote flag is untestable without knowing
  the flag state. `[ASSUMED — verify]` that remote config is in use.

## Known unknowns

- `UNKNOWN — needs manual verification`: whether Bayut UAE and Bayut KSA/Egypt ship from
  one Android binary with locale switching, or separate apps. Changes device matrix and
  data setup entirely.
- `UNKNOWN — needs manual verification`: whether a QA/staging environment exists that the
  Android build can be pointed at, or whether we test against production data only.
  This is the single biggest determinant of test-data strategy.
- `UNKNOWN — needs manual verification`: which areas are native vs webview. Webview areas
  need a different locator strategy and may be untestable with UiAutomator alone.
