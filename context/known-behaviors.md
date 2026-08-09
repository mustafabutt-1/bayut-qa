# Known Behaviors — Quirks, Accepted Oddities, Open Defects

The file that stops us from re-reporting the same non-defect every sprint, and stops
`failure-triage` from classifying a known quirk as a new REAL DEFECT.

**Three sections, three different meanings. Do not merge them.**

- **§1 As-designed quirks** — surprising but intentional. A test asserting otherwise is a
  TEST DEFECT.
- **§2 Known open defects** — real, already filed in ClickUp. A new report is a duplicate.
- **§3 Environment/data artefacts** — not app behaviour at all. Classify as ENVIRONMENT
  or DATA, never as a defect.

Every entry needs: evidence, date, app build, and who confirmed it. An entry without a
confirmer is a rumour and belongs in §4.

**Status:** empty of confirmed entries — nothing has been verified against a real build
yet. The examples below show the required shape and are all `[ASSUMED — verify]`.

---

## §1 As-designed quirks

| ID | Behaviour | Confirmed by | Date | Build | Evidence |
|---|---|---|---|---|---|
| KB-001 `[ASSUMED — verify]` | Result count in the header may exceed the number of listings a user can page to, because results are capped at N pages | TODO | TODO | TODO | TODO |
| KB-002 `[ASSUMED — verify]` | Prices displayed in a non-AED currency are indicative conversions and may drift from the filter range boundaries | TODO | TODO | TODO | TODO |
| KB-003 `[ASSUMED — verify]` | "Newest" sort uses listing *re-activation* date, not original creation date | TODO | TODO | TODO | TODO |
| KB-004 `[ASSUMED — verify]` | Some listings legitimately have no price ("Ask for price") and are excluded from price-filtered results | TODO | TODO | TODO | TODO |

**Rule for agents:** if a failure matches a §1 entry, the outcome is **TEST DEFECT** — the
test's expectation is wrong. Report it as such and propose the case correction.

## §2 Known open defects (already in ClickUp)

| ID | ClickUp ref | Summary | Severity | Affected areas | Status | First seen |
|---|---|---|---|---|---|---|
| — | — | *(none recorded yet)* | — | — | — | — |

**Rule for agents:** before writing a bug report, `bug-report-writer` must check this
table **and** run `tools/clickup_client.py search` for a duplicate. If a match exists,
write a *recurrence note* referencing the existing ticket, not a new report.

## §3 Environment and data artefacts

| ID | Symptom | Real cause | How to confirm | Correct classification |
|---|---|---|---|---|
| ENV-001 | Empty result set on a normally-populated search | Test account / region data reset, or staging DB refresh | Re-run same query in browser on the same environment | DATA |
| ENV-002 | Widespread timeouts across unrelated tests | Device Wi-Fi, proxy down, or mitmproxy cert expired | Check `capture.har` is non-empty; ping the API host from the device | ENVIRONMENT |
| ENV-003 | Every locator fails on one device only | App failed to install/update on that device; stale build | `adb shell dumpsys package <pkg> \| grep versionName` | ENVIRONMENT |
| ENV-004 | Feature missing entirely, tests fail at navigation | Remote feature flag off for this build/account | Compare `/config` response in the evidence bundle across devices | ENVIRONMENT |
| ENV-005 | Arabic tests fail but English pass on same flow | Device locale did not actually switch | `adb shell getprop persist.sys.locale` in the bundle | ENVIRONMENT |
| ENV-006 | Listing disappears mid-run | Listing genuinely expired or was removed by the agency — production data is live | Query the listing ID directly; check for 404 vs 200 | DATA |

**ENV-006 is important.** Testing against live production inventory means our test data
mutates under us. Until we have a stable seeded environment (`docs/ASKS.md`), tests must
select listings dynamically from the current result set, never by hardcoded ID.

## §4 Unconfirmed folklore

Things people say the app does that nobody has evidenced. Living here means an agent must
treat the topic as `UNKNOWN — needs manual verification`, not as fact.

- `UNKNOWN`: whether filters persist across app backgrounding.
- `UNKNOWN`: whether the Arabic locale returns an identical result set to English for the
  same query. **If it does not, that is a defect, not a quirk** — but confirm first.
- `UNKNOWN`: whether the lead POST is fire-and-forget (UI shows success regardless of
  server response).
- `UNKNOWN`: whether pagination is offset- or cursor-based, and whether new listings
  entering mid-scroll cause duplicates or skips.

## Promotion rules

- §4 → §1 requires: reproduced twice, on two devices, with evidence attached, plus a dev
  or PM confirming intent. Record who confirmed it.
- §4 → §2 requires: a filed ClickUp ticket ID.
- Any §1 entry that a PM later calls unintended moves to §2 and every test that encoded
  the quirk gets corrected. Log the move in `docs/DECISIONS.md`.
- §2 entries are reviewed every release; fixed ones are deleted, not archived here.
