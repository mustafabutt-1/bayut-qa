# Audit history — Price Filter

One row per cycle. Kept so that a *pattern* of failures is visible across features: if
uncited expectations show up every cycle on every feature, the fix belongs in
`.claude/agents/feature-test-designer.md`, not in the individual case set.

---

## Cycle 1 — 2026-08-12 — `FAIL`

**Blocking: 5 · Advisory: 3 · Scenarios: 21** (5 observed, 14 assumed, 2 fabricated)

| Item | Issue |
|---|---|
| B1 | Two scenarios cited `probe P6` with a fabricated date and build. `tools/prober.py` implements P1–P5; `context/filter-behaviour.md` does not exist. |
| B2 | `Then the result count matches the API totalCount` — no API oracle exists; unobservable by human or tool. |
| B3 | `Then the price filter still works correctly` — unfalsifiable. |
| B4 | `Then the results are filtered to that range` — restated the When step. |
| B5 | Asserted a listing at exactly 120,000 exists in live inventory (D-007). |

**Auditor's note:** `_feature.md` correctly stated "there is no boundary-inclusivity probe…
do not cite a probe id that does not exist" — and two scenarios then did exactly that.
The honest summary and the fabricated assertion were in the same commit.

---

## Cycle 2 — 2026-08-12 — writer revision

**Changed (5 blocking items, all addressed — no disputes):**

| Item | Response | What changed |
|---|---|---|
| B1 | **Fixed** | Removed both `probe-P6` citations; `@source:probe-P6` → `@source:assumed`; both scenarios now carry `[ASSUMED — needs verification]` with an explicit note that no probe has run. |
| B2 | **Fixed** | Deleted the `API totalCount` assertion from `happy-path.md`. Parked in `_feature.md` → "Blocked on the API oracle" with the unblock condition, rather than dropped silently. |
| B3 | **Fixed** | "works correctly after rotating" → "An entered minimum survives device rotation", with two observable assertions. Case kept, not deleted — an EditText losing its value on configuration change is a real defect class. |
| B4 | **Fixed** | Replaced with the relational form already used correctly elsewhere in the set: "no listing priced above 120,000 appears in the results". |
| B5 | **Fixed** | The listing at the bound became a `Given` precondition the tester establishes from unfiltered results and skips if unmet, instead of an assertion about live inventory. Also replaced "Dubai Marina" with the sanctioned test location per `docs/GUARDRAILS.md` §3 — an unflagged production-data issue found while fixing B5. |

**Advisories:**

| Item | Response | Rationale |
|---|---|---|
| A1 | **Declined** | The four assertions are one behaviour — "the sheet opens with its documented defaults". Splitting them would produce three near-identical scenarios differing only in which default they read, which is the copy-paste pattern the format rules prohibit. Accepted the weaker failure message as the better trade. |
| A2 | **Fixed** | `coverage.md` Outline now states explicitly that its `Examples` block is a 5-row sample and the 30-row array table above is the source of truth. |
| A3 | **Deferred, declared** | Real gap: the array assigns `entry_point=full_filters_sheet` to 8 of 30 rows while only one scenario is tagged `@entry:full-filters-sheet`. Fixing it needs a *new* scenario, which the revision protocol forbids unless a blocking item requires it — and A3 is advisory. Recorded as a coverage gap in `_feature.md` for the next writing pass rather than smuggled into a revision cycle. |

**Scenario count: 21 → 21.** No scenarios added or removed, per the revision protocol.

---

## Cycle 2 re-audit — 2026-08-12 — `PASS_WITH_NOTES`

**Blocking: 0 · Advisory: 4 · Scenarios: 21** (5 observed, 16 assumed, **0 fabricated**)

All five cycle-1 blocking items verified fixed by re-running the checks that produced
them, not by reading the writer's account of the fix:

- `@source:probe-*` count across all four case files is **0** (was 2)
- no `API totalCount`, `works correctly`, or `filtered to that range` in any live Gherkin
  step — remaining textual matches are inside `#` explanation comments
- the bound-listing is a `Given` precondition, not a `Then` assertion
- all 5 `@source:observed` citations re-opened and confirmed

**Loop converged in 2 of a permitted 3 cycles. No disputes.**

### Pattern to watch across features

Two things belong in the agent specs rather than in this case set:

1. **The auditor missed a production-safety issue in cycle 1** — a scenario searching
   "Dubai Marina", real brokerage inventory, against `docs/GUARDRAILS.md` §3. The writer
   caught it while fixing B5. Check C in `test-case-auditor.md` should include a
   sanctioned-test-data check. **If this recurs on the next feature, fix the spec.**
2. **The fabricated-probe defect (B1) came from the format example.** The writer copied
   `@source:probe-P6` from a template that used P6 illustratively. Templates that carry
   plausible-but-fake citations get copied. If B1-shaped items recur, the fix is to make
   every example in `feature-test-designer.md` cite something real or something obviously
   placeholder — never something that looks real and is not.
