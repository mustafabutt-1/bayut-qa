# Project State

**The status file. Read this before doing anything else in this repo.**

Do not infer project status from the file tree. Several files look complete and are
deliberately hypotheses. This document is the single source of truth for what is real.

- **Last updated:** 2026-08-09
- **Phase:** 0.5 complete (context tooling). Phase 1 not started.
- **Hard blocker:** no Android device has ever been connected. Every tool is verified
  against synthetic fixtures only. Nothing has touched the real Bayut app.

> **Keep this file current.** Whoever finishes a phase updates the tables below and the
> "Next action" section in the same commit. A stale state file is worse than none — it
> makes a new person confidently wrong.

---

## 1. What is built and verified

All five context tools run end-to-end with no device, against `tests/fixtures/`.

| Tool | Lines | Verified by |
|---|---|---|
| `tools/pagesource.py` | 415 | fingerprint + diff across EN/AR fixtures |
| `tools/crawl_safety.py` | 790 | `selftest` — **119/119 assertions** (19 block + 11 production-block + 10 allow rules, plus the lead gate) |
| `tools/adb.py` | 684 | `--dry-run` across every subcommand |
| `tools/crawler.py` | 925 | `offline` mode → all 7 reports generated |
| `tools/prober.py` | 767 | `selftest` — **28/28 assertions** |
| `tools/pairwise.py` | 694 | `selftest` — **24/24 assertions**, incl. brute-force coverage verification, determinism, and the real `filter-inventory.md` model |

Reproduce all of it in about 20 seconds:

```bash
python tools/crawl_safety.py selftest          # expect 119/119
python tools/prober.py selftest                # expect 28/28
python tools/crawler.py offline --fixtures-dir tests/fixtures/page_source --out /tmp/check
python tools/crawl_safety.py --app-package com.bayut.app check \
    --page-source tests/fixtures/page_source/02-listing-detail.xml
```

The last command must show Call, WhatsApp, Email, Share and Report all **BLOCK**, plus
Save property as `PROD-BLOCK-FAVOURITE`. If it does not, stop — do not crawl.

**Guardrails are live.** Environment defaults to PRODUCTION everywhere; regression
cannot create data on production; leads are permitted only on Explorer Real Estate
via an evidence-gated exemption. Full policy in `docs/GUARDRAILS.md` — read it before
touching a device.

## 2. What is NOT built

| Item | Status | Blocked by |
|---|---|---|
| `tools/testmo_client.py` | not started | nothing — needs a Testmo token to test live |
| `tools/clickup_client.py` | not started | nothing — read-only by construction (D-004) |
| `tools/evidence.py` | not started | nothing — takes fixture paths |
| `tools/oracle.py` | **deliberately waiting** | crawl must first answer: is traffic interceptable, and is exact listing-ID matching possible |
| `tools/har_diff.py` | **deliberately waiting** | same — pointless if certificates are pinned |
| `tests/conftest.py` | placeholder that raises | Phase 2 |
| `tests/screen_objects/` | empty | needs real locators from a crawl |
| `templates/*.md` | empty | Phase 4 |
| 12 of 13 agents | not written | Phase 3 — see `.claude/agents/README.md` |
| `docs/ROLLOUT.md`, `ASKS.md`, `RISKS.md` | not written | Phase 5 |

## 3. What is a hypothesis, not a fact

**Exception — `context/regression-checklist.md` is EVIDENCE, not hypothesis.** Extracted
from the QA team's own regression checklist (2026-08-09), it outranks every file below and
already contradicts several. Section 1 of that file lists nine corrections that have
**not yet been applied** to the sources — most importantly that the app's own vocabulary
is **LPV/DPV**, not SRP/LDP, and that there are **four** locales (en, ar, ru, zh), not two.

Everything else in `context/`, except the two `.example.yaml` templates, was written from
inference about a UAE property portal and has not been checked against the app.

| File | Status |
|---|---|
| `context/feature-map.md` | 36 feature areas, 4 tiers. Tiering is judgement, case counts are all `TODO`. |
| `context/filter-inventory.md` | 20 filters + 5 axes + a YAML block with 14 params and 7 constraints. **Every constraint is a guess.** A wrong constraint silently deletes valid combinations from every generated suite. |
| `context/screen-inventory.md` | Hand-written. Will be replaced by `screen-inventory.observed.md` from the crawl. |
| `context/api-contracts.md` | Shape only. No capture has ever been taken. |
| `context/known-behaviors.md` | Empty of confirmed entries by design. |
| `context/device-matrix.md` | No real devices recorded. |
| `context/terminology.md` | **Arabic strings are translations, not the app's own.** Asserting on them would manufacture false defects. |

The 144 existing Testmo cases have **not** been exported or mapped to feature areas.
`suite-curator` and `regression-scoper` cannot function until they are.

## 4. Environment verified on the original machine

Confirmed working 2026-08-09. See `docs/SETUP.md` to reproduce elsewhere.

| Component | Version | Note |
|---|---|---|
| Appium server | 3.5.2 | probed `/status` → ready |
| uiautomator2 driver | 8.1.0 | the one we need |
| Node / npm | 24.9.0 / 11.6.0 | |
| Python | 3.13.7 | 3.11+ required |
| Appium-Python-Client | 6.0.0 | in `.venv`. **6.x pairs with server 3.x** — 4.x is for server 2.x |
| selenium | 4.46.0 | pulled by the client |
| adb | present | path is machine-specific — set `ADB_PATH` in `.env` |
| **Physical device** | **none** | the hard blocker |
| mitmproxy | not installed | needed for the pinning check |

## 5. Open decisions — needed from the QA lead

These block work and cannot be decided by whoever picks up the repo.

| # | Decision | Consequence of each option |
|---|---|---|
| 1 | ~~Staging or production?~~ **ANSWERED 2026-08-09: production, until told otherwise.** | Enforced in code. Consequence: automation on production is **read-path automation**; sign-up, favourites, saved searches, reports, claims, seller leads and BayutGPT stay manual. A staging environment is the single change that unlocks them. |
| 2 | **Locale switching method** | There is **no reliable pure-adb locale switch** on a non-rooted device. Options: rooted test device / ADB Change Language helper APK / the app's own language setting. Blocks the entire `arabic` marker. |
| 3 | **Test account** | Must be a QA account with a phone number we control. Never a real user's. |
| 4 | **mitmproxy host ownership** | Needs a stable IP reachable from the device. If the office network reassigns it, every run breaks. |
| 5 | **Tier placement in `feature-map.md`** | Business judgement. Is TruCheck a Tier-1 trust differentiator or Tier-2? |

## 6. Known risks already identified

| Risk | Impact | Status |
|---|---|---|
| **Certificate pinning** | Kills `oracle.py` and `har_diff.py` — the most differentiated part of the design | UNRESOLVED. The watchdog reports within 5 min of the first crawl. Mitigation is a dev debug build trusting user CAs. |
| **Listing ID not visible in UI** | `oracle.py` degrades to fuzzy price+title matching, weakest exactly where a dropped listing is most likely | UNRESOLVED. `listing-id-visibility.md` answers it. |
| **No stable testIDs** | Suite does not survive past ~20 tests | UNRESOLVED. `locator-quality.md` produces the itemised ask. |
| **Arabic blocklist patterns unverified** | A missing Arabic form is a *safety* gap, not a coverage gap | Mitigated: AR crawl runs STRICT only until the first crawl confirms real labels. |
| **Live production inventory mutates** | Tests cannot use hardcoded listing IDs (D-007) | Accepted. Tests select dynamically. |
| **Accidental lead to a real agency** | Real money, real relationship damage, programme-ending | Mitigated in code: blocked by default; the only exemption reads the agency off the screen and covers Explorer Real Estate alone. |
| **Accidental data creation on production** | Pollutes real accounts, alert emails, moderation queues, LLM spend | Mitigated: 11 production-only block rules, active by default. |
| **Credentials leaking into the repo** | Six live accounts exist in the source checklist PDF | Mitigated: referenced by env-var name only; `.env` gitignored. Rotate if ever committed. |
| **Algolia sync means counts differ app vs web** | A naive oracle would report false positives | Mitigated by design: `oracle.py` compares only within a single request. See `context/regression-checklist.md` section 4. |

## 7. Next action

**If a device is available:** run Session 1 in `README.md` → "First crawl". Then read, in
this order:

1. `context/pinning-check.md` — does the API oracle exist at all?
2. `context/listing-id-visibility.md` — exact matching or fuzzy?
3. `context/crawl-uncertain.md` — the review queue that unlocks a deeper second crawl

**If no device is available:** build the device-independent Phase 1 tools —
`pairwise.py`, `testmo_client.py`, `clickup_client.py`, `evidence.py`. Do **not** build
`oracle.py` or `har_diff.py`; their design depends on crawl outputs, and guessing means
rewriting the most valuable check in the system.

## 8. Session log

Append one line per working session so the next person can see the trail.

| Date | Who | What happened |
|---|---|---|
| 2026-08-09 | guardrails | Production-by-default enforced in code; 11 production data-creation block rules; evidence-gated lead exemption limited to Explorer Real Estate; `--environment` threaded through all three tools. selftest 65 to 117. Regression checklist ingested as `context/regression-checklist.md` — it corrects 9 Phase 0 hypotheses and adds 13 unmapped feature areas. |
| 2026-08-09 | initial build | Phase 0 scaffold + context hypotheses. Phase 0.5 tooling built and verified offline. `crawl_safety` selftest caught 4 real gaps (word-boundary bugs in block patterns) before any device contact. Fixed a crawl-loop bug where a `for/else/break` ended the entire crawl on the first dead end. Corrected `requirements.txt`: Appium client 4.3.0 → 6.0.0 for server 3.x. |
| 2026-08-10 | session | Re-verified all four toolchain commands on a fresh clone — 65/65, 28/28, 3 screens/10 blocked, all 5 lead controls BLOCK. Found this machine has no `.venv` and a global Appium-Python-Client 4.5.0 (needs 6.0.0 for the installed server 3.6.0); `allpairspy`/`mitmproxy` not installed; no `.env`; no device connected. Added `docs/REGRESSION-CHECKLIST.md` — the manual QA team's own human-authored regression checklist (not a crawler output), transcribed with test-account credentials redacted into new `.env.example` entries. Not yet merged into `context/feature-map.md` — that tiering call is still open decision #5. |
