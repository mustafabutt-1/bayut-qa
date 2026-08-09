# Architecture

How the system works and why it is shaped this way. If you only read one other file,
read `docs/PROJECT-STATE.md` — this document explains the design, that one says how much
of it is real.

---

## 1. Three constraints generate the whole design

**1. No source code access.** Every fact about the app must come from the screen (page
source), the wire (mitmproxy), or production signal (Crashlytics, store reviews, support
tickets). There is no "go check the implementation" fallback. This is why `context/`
exists as its own layer: it is the app's behaviour written down, and it is the *only*
thing agents are allowed to know about the app.

**2. The app is production, with a real account.** Some taps cost real money — a
contact-agent tap sends a billable lead to a real Dubai agency. This is why the safety
layer sits *beneath* the crawl layer rather than being a feature of it.

**3. Agents hallucinate silently in exactly the wrong places.** A model asked for a
covering array produces something that looks right and is not, and nobody can see the
difference by reading it. This produces the governing rule of the codebase:

> **If being wrong would be invisible, it goes in Python.**

| Invisible when wrong → Python | Visible when wrong → Agent |
|---|---|
| covering arrays, coverage math | "is this a real defect or a flake?" |
| constraint semantics | "which 30 of the 144 cases matter this release?" |
| set diffing (API vs UI) | "what is ambiguous in this ticket?" |
| log trimming windows | "how do I word this so dev acts on it?" |
| block / allow tap verdicts | "is this worth escalating to Ted?" |

---

## 2. The layer stack

```
  adb.py            device: reset app, set proxy, deep link, logcat, screenrecord
     │
  pagesource.py     XML → Element objects → fingerprint, locator, stability
     │
  crawl_safety.py   Element → BLOCK / ALLOW / UNCERTAIN          ← the gate
     │
  crawler.py        PASSIVE: walk the app, never tap through the gate
  prober.py         PROBE:   change one filter, read the count delta
     │
  context/*.md      observed facts — the ONLY thing agents read about the app
     │
  agents            design tests, triage failures, write reports
```

Each layer knows only about the one below it. `crawler.py` cannot tap without going
through `crawl_safety.py`. There is no second tap path.

---

## 3. The tap gate

Every tap routes through `SafetyPolicy.may_tap()`, in both `crawler.py` and `prober.py`.
This is why the guard is its own module rather than living inside the crawler (D-010):
PROBE mode taps too — filter options, apply, reset — and two tap paths means two things
to audit and one to forget.

```
Element
  │
  ├─ 19 BLOCK rules ────────────── match? ──→ BLOCK   never tapped, in any mode,
  │                                                    no flag disables this
  ├─ package != app under test ─── yes? ────→ BLOCK   foreign app: dialer, WhatsApp,
  │                                                    browser, store, permission UI
  ├─ 10 ALLOW rules ────────────── match? ──→ ALLOW   tapped
  │
  └─ matched nothing ───────────────────────→ UNCERTAIN
                                                strict (default): logged, not tapped
                                                permissive: tapped, explicit flag only
```

**Block is evaluated first and always wins.** There is no configuration that disables
the blocklist. The YAML extension file may only *add* rules.

### Dual-form matching

Each rule regex is tested against the raw attribute value **and** a variant where
`_ - . :` become spaces. This exists because `call_agent_button` does **not** match
`\bcall\b` — underscore is a word character. The selftest caught this before any device
was touched; without it, a content-desc'd call button would have been tapped.

### What is deliberately NOT blocked

As considered as what is:

| Not blocked | Why |
|---|---|
| bare `Buy` / `شراء` | the purpose toggle. Blocking it kills the crawl. Only `Buy Now`, `Checkout`, `Subscribe`, `Payment` are commerce. |
| `Save` / `Favourite` | non-destructive, reversible. But `Remove from Favourites` **is** blocked. |
| `Search`, `Filters`, filter chips | the surface we are here to map |

### The selftest is the proof

51 strings that must block, 13 that must not, 1 foreign-package case. Runs with no
device in under a second. **Run it before every crawl session.**

Hardest verified case — the Arabic email button, which has no resource-id and no
content-desc, only Arabic text:

```
BLOCK  البريد الإلكتروني   BLOCK-LEAD-EMAIL   ← caught on text alone
```

**Honest limitation:** those Arabic patterns are `[ASSUMED — verify]`, written from
general usage rather than Bayut's shipped strings. A missing Arabic form is a *safety*
gap, not a coverage gap. The AR crawl therefore runs STRICT only until a first crawl
confirms the real labels.

---

## 4. Screen fingerprinting

```python
fingerprint = sha256(sorted({resource-id for each element}))[:12]
```

Three exclusions, each deliberate:

- **`text` excluded** — changes with every listing that loads. Include it and every
  scroll looks like a new screen.
- **`content-desc` excluded from the structural fingerprint** — it is a *localized*
  string, the thing TalkBack reads aloud. Including it made the same screen fingerprint
  differently in English and Arabic, breaking "same fingerprint means same screen"
  exactly where the cartographer compares locales (D-012).
- **`bounds` excluded** — shifts with content and display density.

A second `full_fingerprint` *does* include `content-desc`, which yields a free
diagnostic: **when the two fingerprints are identical, the screen carries no
accessibility labels at all.** That is simultaneously a TalkBack gap and a locator
problem, so it is reported as both.

Observed on the fixtures:

```
EN listing detail:  structural 85369dd78ff5   full 254742e3c3ac
AR listing detail:  structural 4987d632e131   full ace73874a035

structural diff → 7 resource-ids present in EN, absent in AR:
  btn_email_agent, btn_share, agent_card, agent_name, agency_name,
  ldp_location, section_floorplan
```

That is the shape of a real finding: the AR build exposes fewer identifiers.

---

## 5. The crawl loop and the action budget

```
pm clear → launch → capture(home) → queue = [([], home_fp)]

while queue and budget > 0:
    path, origin = queue.popleft()
    if depth(path) >= max_depth: skip
    navigate(path)              ← replay from a fresh reset; costs actions
    capture, record screen

    for each tappable element:
        budget exhausted?   → stop_crawl = True, break      (ends the crawl)
        screenshot
        safety gate         → BLOCK/UNCERTAIN: log, skip
        tap                 → budget -= 1, sleep 800ms
        capture
        new fingerprint?    → record edge; if unseen, enqueue path
        back
        capture
        back landed wrong?  → log dead end, pm clear, break  (skips this screen only)
```

**Why replay instead of a stateful walk.** Re-walking from a reset costs actions but
guarantees known state. A stateful walk accumulates drift — a dismissed tooltip here, a
loaded page 2 there — and by depth 4 you are mapping a state you cannot reproduce. The
400-action cap makes the trade bounded and affordable.

**The budget is a safety mechanism, not a performance knob.** `max_actions` is validated
against a hard `ACTION_CAP = 400` that can be lowered but never raised, and
`action_interval` cannot go below 800ms.

**Expect a partial map on run one.** Strict mode + replay cost + 400 actions means the
first crawl maps a fraction of the app. That is the design: *a partial map you trust
beats a complete map you do not.*

> **Bug fixed 2026-08-09.** The inner loop used `for...else` such that a dead end broke
> the *outer* while loop, ending the entire crawl at the first back-navigation failure
> while reporting "completed". Now an explicit `stop_crawl` flag distinguishes
> budget-exhaustion (end the crawl) from a dead end (skip this screen only).

---

## 6. Probe inference

A passive crawl proves a filter exists. It cannot say whether amenities AND or OR.
So: **the result count is the instrument.** Set a known state, read the count, change
one thing, read again.

```
Count(Private Pool) = 812
Count(Maids Room)   = 204
Count(both)         =  96

96 ≤ min(812,204)=204   → AND   (intersection: narrows)
   ≥ max(812,204)=812   → OR    (union: widens)
   strictly between     → UNRESOLVED — record raw numbers, re-probe
```

The third branch matters. A count of 500 fits neither model — result caps, dedup, or
relevance trimming are all possible. The system says UNRESOLVED rather than picking the
closer answer.

### P4 is the highest-stakes probe

Three verdicts that must never collapse into each other (D-014):

| Verdict | Observation | Meaning |
|---|---|---|
| `PREVENTED` | greyed out / untappable | a real pairwise constraint — **keep it** |
| `ALLOWED_EMPTY` | selectable, returns 0 | a **valid empty-state test case** — not a constraint |
| `CONSTRAINT_WRONG` | selectable, returns results | the assumption was false — **delete it** |

Collapsing `ALLOWED_EMPTY` into `PREVENTED` deletes that combination from every
generated suite forever, and the suite still looks full. This is the single most likely
way this programme produces confident, invisible under-coverage.

### Count parsing

Handles Arabic-Indic digits (`١٬٢٤٧ عقار` → `1247`) and returns `None`, never `0`, when
no number is present. A missing count and a genuine zero mean completely different
things, and conflating them would turn a broken locator into a false "zero results"
defect.

### Why the inference is pure functions

`infer_and_or(812, 204, 96) → AND` needs no device, so the reasoning is unit-testable
and auditable. Every probe result is written alongside the **raw counts that produced
it**, so a human can check the inference rather than trust it.

---

## 7. The pinning watchdog

A daemon thread samples the mitmproxy flow file every 15 seconds during the crawl.

```
file grows          → TRAFFIC_SEEN, print immediately, stop watching
5 min, no growth    → PINNING_SUSPECTED, loud multi-line warning mid-crawl
no flow file given  → MITM_NOT_CONFIGURED, warn at startup
crawl ends first    → INCONCLUSIVE
```

Why a thread and not a post-run check: if the app pins certificates, `oracle.py` and
`har_diff.py` are both dead, and that is the most differentiated part of this design.
Learning it in minute five changes what you do that day; learning it after a 40-minute
crawl wastes the session (D-013).

It reports **SUSPECTED, never CONFIRMED** — zero traffic is also consistent with
non-HTTP transport or a misconfigured proxy — and prints a two-step human confirmation
alongside the warning.

---

## 8. End-to-end data flow

```
  DEVICE
    │  adb.py: pm clear, proxy set, deep link, logcat
    ▼
  Appium ──── page_source XML ──→ pagesource.py ──→ Element[]
    │                                                  │
    │                                        crawl_safety.py
    │                                                  │
    │  ◀──── tap (only if ALLOW) ──────────────────────┘
    ▼
  crawler.py / prober.py
    │
    ├──→ context/page_source/*.xml           raw evidence, kept
    ├──→ context/screen-inventory.observed.md
    ├──→ context/element-inventory.json      → feeds flow-builder later
    ├──→ context/screen-graph.mermaid
    ├──→ context/locator-quality.md          → becomes docs/ASKS.md
    ├──→ context/listing-id-visibility.md    → decides oracle.py's design
    ├──→ context/filter-behaviour.md         → updates filter-inventory.md YAML
    ├──→ context/crawl-blocked.md            → the manual-test-only list
    ├──→ context/crawl-uncertain.md          → the human review queue
    └──→ context/pinning-check.md            → decides if the oracle exists at all
                        │
                        ▼
              context/*.md  ── the ONLY thing agents know about the app
                        │
                        ▼
      test-designer → pairwise.py → Testmo drafts → flow-builder → pytest
                        │
                  run → failure → failure-triage → bug-report-writer
                        │                            ↓
                        │                     reports/*.md (unverified)
                        │                            ↓
                        │                     human reviews → files in ClickUp
```

### Two feedback loops worth naming

**Reach expansion.** `crawl-uncertain.md` → human review → `crawl-allowlist.yaml` →
deeper crawl. This is how the system safely learns what it is allowed to touch.

**Drift detection.** Re-crawl every build → `drift-report.md`. Changed accessibility ids
break tests silently. Catching them *before* the suite goes red is arguably worth more
than the initial map, because it turns a mystery failure into a known change.

---

## 9. Report outputs and what each is for

| Output | Consumer | Why it matters |
|---|---|---|
| `screen-inventory.observed.md` | humans, `flow-builder` | screens, entry paths, element counts by stability |
| `element-inventory.json` | `flow-builder` | machine-readable locators for test generation |
| `screen-graph.mermaid` | humans, the pitch | makes unreachable screens obvious |
| **`locator-quality.md`** | **dev, via `docs/ASKS.md`** | every weak element with a *suggested* accessibility id — turns a QA complaint into a one-line PR. Frame as accessibility compliance, not a QA favour. |
| **`listing-id-visibility.md`** | `oracle.py` design | exact ID matching, or degrade to fuzzy price+title — weakest exactly where a dropped listing is most likely (near-identical units in one tower) |
| `crawl-blocked.md` | human testers | enumerates every consequential control — precisely the set that must stay manual |
| `crawl-uncertain.md` | human reviewer | the queue that unlocks deeper crawls |
| `pinning-check.md` | programme decision | whether the API oracle is buildable at all |
| `filter-behaviour.md` | `filter-inventory.md` | observed filter semantics with raw counts attached |

---

## 10. Design decisions index

Full rationale in `docs/DECISIONS.md`. The load-bearing ones:

| # | Decision |
|---|---|
| D-003 | Combinatorics live in `pairwise.py`, never in a prompt |
| D-004 | `clickup_client.py` is structurally read-only — no create method exists at all |
| D-006 | Listing ID is the oracle key; price+title matching is ambiguous in the case that matters |
| D-008 | Retry gathers evidence, never turns a run green |
| D-009 | `context/` is generated by crawling, not hand-written |
| D-010 | The safety guard is a shared module — crawler and prober use one implementation |
| D-011 | Default-deny with UNCERTAIN as a first-class outcome |
| D-012 | Fingerprints are structural (resource-id only), so they survive locale changes |
| D-013 | Pinning is reported by a watchdog mid-crawl, not in the final report |
| D-014 | PREVENTED / ALLOWED_EMPTY / CONSTRAINT_WRONG stay distinct |
