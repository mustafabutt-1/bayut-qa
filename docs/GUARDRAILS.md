# Guardrails — Production Testing Policy

**Binding.** Every tool, agent and test in this repo obeys these. They are enforced in
code where possible (`tools/crawl_safety.py`), not left to discipline.

---

## The four rules

### 1. The environment is PRODUCTION until told otherwise

Not "probably production". Not "production for now". **Production, by default, every
time, in every tool**, until a human explicitly passes `--environment staging`.

There is no auto-detection and no "this URL looks like staging" inference. Guessing wrong
in that direction writes real data to a live property portal used by real brokers.

```python
SafetyPolicy()                        # environment == "production"
SafetyPolicy.load()                   # environment == "production"
crawler.py crawl ...                  # PRODUCTION
crawler.py crawl --environment staging  # only way to opt out, and it is explicit
```

The environment is recorded in the header of every generated report, so no artifact is
ever ambiguous about which environment produced it.

### 2. Regression must not create data on production

Anything that persists server-side is blocked while the environment is production. Eleven
rules, active only on production, listed in full below.

The distinction the rules draw is **write vs. read**: the Favourites *tab* stays
reachable, the favourite *heart* does not. The TruEstimate landing screen stays
reachable, *Generate Report* does not. Blocking the destination as well as the action
would make half the app unmappable for no safety gain.

### 3. Leads only on Explorer Real Estate

A lead is the revenue event and it reaches a real brokerage. Exactly one agency is
allowlisted:

```
LEAD_TEST_AGENCIES = ("Explorer Real Estate",)
LEAD_TEST_LOCATION = "Al Napoca"
```

Both come from the regression checklist. Explorer Real Estate is Bayut's own demo /
testing agency, so a lead there reaches us rather than a paying customer.

**The gate reads the screen; the caller does not get to assert.** `authorise_lead()`
parses the live page source and looks for an allowlisted agency name itself. A test
saying "trust me, this is Explorer Real Estate" is exactly how a real brokerage ends up
with a fake enquiry.

```python
with policy.lead_test(parse_page_source(driver.page_source)) as auth:
    # Call / WhatsApp / Email CTAs are tappable here, and only here
    ...
# outside the block they are blocked again, automatically
```

Refuses with `LeadNotAuthorised` when the agency is not on screen. The exemption covers
`lead_contact` rules **only** — logout, delete, moderation, commerce and every production
data-creation rule stay blocked inside the block, and the exemption cannot leak past it.

Crawler and prober never call this. They are exploration, and exploration never
generates a lead.

### 4. No credentials in this repository

The regression checklist PDF contains six sets of live test-account credentials. **None
of them are in this repo and none may be added.** They belong in `.env`, which is
gitignored, referenced by variable name only.

This repo is pushed to GitHub. A credential committed once is a credential that must be
rotated, even if the commit is later removed.

---

## The production blocklist

Active only when `environment == production`. On staging these become tappable again.

| Rule | Blocks | Because |
|---|---|---|
| `PROD-BLOCK-SIGNUP` | Sign Up, Create account, Register | Creates a real account. Deletion is a separate support burden and an App Store review surface. |
| `PROD-BLOCK-SAVE-SEARCH` | Save this search, Alert Me of New Properties | Persists a saved search; triggers recurring alert emails and push to a real inbox. |
| `PROD-BLOCK-FAVOURITE` | the favourite heart, Save property, Add/Remove from Favourites | Writes account data; pollutes Activity Log and recommendation signals. The checklist treats favourites as persisted state that must survive an app override. |
| `PROD-BLOCK-TRUESTIMATE-REPORT` | Generate/New/Create/Download Report, Confirm Details | Persists a report, emails it out, and triggers the App Review bottom sheet. |
| `PROD-BLOCK-PORTFOLIO` | Add to Portfolio | Persisted account data. |
| `PROD-BLOCK-CLAIM-TRANSACTION` | Claim / Submit / Resubmit Claim | Reaches Nova for human moderation and locks the transaction for other agents. |
| `PROD-BLOCK-SELLER-LEADS` | Sell My Property, Seller leads | Creates a real seller lead. |
| `PROD-BLOCK-BAYUTGPT-SEND` | BayutGPT entry points | Costs a real LLM call and persists chat history. Blocked at the entry point deliberately — every interaction on that screen sends a query. Map it manually. |
| `PROD-BLOCK-PROFILE-EDIT` | Edit Profile, Save changes | Mutates the real account. |
| `PROD-BLOCK-SHARE-REPORT` | Share Report / Transactions / Story / achievement | Generates a persisted shareable artifact and reaches external platforms. |

Blocked in **every** environment (these are not production-specific): lead contact,
logout, account deletion, delete/remove, report-to-moderation, commerce, notification
opt-in, share, external links, foreign packages, system permission dialogs.

`Contact Us` intentionally has no production rule — `BLOCK-LEAD-CONTACT` already catches
it everywhere. A rule that can never fire reads as coverage that is not there.

---

## What this means in practice

### The crawler will map less of the app

Expect a large `crawl-blocked.md`. That file is not a failure report — it is the
**manual-test-only inventory**, and it is a genuinely useful artifact: it enumerates
every control in the app with a real-world consequence.

Roughly, on production the following stay **manual**: sign-up and login flows, account
deletion, saved searches and alerts, favourites, TruEstimate report generation, Portfolio,
Claim Transactions, Seller Leads, BayutGPT, profile editing, all sharing, and every lead
CTA outside Explorer Real Estate.

That is most of the checklist's write-side coverage. **Automation on production is
read-path automation.** Say so plainly to management rather than implying otherwise — the
honest pitch is that automation covers search, filters, listing rendering, navigation,
locale, currency, and the API-oracle checks, and frees human time for the write flows.

### Getting more automated coverage requires an environment, not a looser guard

The single change that unlocks the write paths is a non-production environment with
seeded data. Until then, do not relax these rules to gain coverage — that is trading a
real-money incident for a metric.

This belongs in `docs/ASKS.md` when it is written.

---

## Verifying the guardrails

Before every crawl session, and after any change to `crawl_safety.py`:

```bash
python tools/crawl_safety.py selftest
#   expect: 119/119 assertions passed
#           default environment : production
#           lead allowlist      : ['Explorer Real Estate']
```

The 117 assertions include:

- 51 dangerous strings that must block, EN and AR
- 13 navigation strings that must **not** block, so the guard cannot silently kill the crawl
- 17 production writes that must block on production **and** must be reachable on staging
- 7 read-only destinations that must stay reachable even on production
- 9 lead-gate assertions: blocked by default; refused for the wrong agency; allowed for
  Explorer Real Estate; the exemption is narrow (Delete/Logout/Report/Sign Up still
  blocked inside the block); and it does not leak after the block exits

Inspect the effect on a real screen:

```bash
python tools/crawl_safety.py --app-package $BAYUT_APP_PACKAGE check \
    --page-source context/page_source/<screen>.xml                    # production
python tools/crawl_safety.py --app-package $BAYUT_APP_PACKAGE \
    --environment staging check --page-source ...                     # compare
python tools/crawl_safety.py rules                                    # every active rule
```

---

## Changing these rules

- **Adding** a block rule: always fine. Add it to `context/crawl-allowlist.yaml` under
  `block:` or `production_block:`, or to the defaults in code.
- **Removing or narrowing** a block rule: code change, reviewed, with a `docs/DECISIONS.md`
  entry saying why. There is deliberately no way to remove a default block rule from
  configuration.
- **Adding an agency to the lead allowlist**: requires confirmation that the agency is
  Bayut-owned test inventory, not a customer. One agency is on it today for a reason.
- **Switching the default environment away from production**: don't. Pass the flag per
  run instead, so every invocation is explicit about what it is touching.

---

## Open questions this policy depends on

- `[ASSUMED — verify]` that **Al Napoca** listings are exclusively Explorer Real Estate.
  The checklist pairs them for lead verification but does not state exclusivity. If other
  agencies have listings there, searching Al Napoca is not on its own sufficient — the
  per-screen agency check is what actually protects us, which is why the gate reads the
  screen rather than trusting the search location.
- `UNKNOWN — needs manual verification`: whether a staging/QA environment exists that the
  Android build can be pointed at. This decides how much of the checklist can ever be
  automated.
- `UNKNOWN — needs manual verification`: whether lead-generating calls can be safely
  intercepted and stubbed via mitmproxy instead of reaching the backend. If they can, the
  lead flows become testable on production without generating leads — potentially the
  highest-value unlock available. Depends on certificate pinning.
