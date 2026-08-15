# Audit — Price Filter

```yaml
verdict: PASS_WITH_NOTES
audited: 2026-08-12T11:34:00Z
build: 15.7.2 (1272)
cycle: 2
summary: >
  All five cycle-1 blocking items fixed and re-verified against source. No fabricated
  citations remain. 16 of 21 scenarios are explicitly [ASSUMED — needs verification],
  which is correct for a feature whose behaviour has never been probed — and is the
  honest number, not a weakness in the case set.

blocking: []                   # all cycle-1 items resolved; none new

resolved:
  - id: B1
    status: FIXED
    verification: >
      `grep -rn "probe-P6" test-cases/price-filter/*.md` returns hits only inside
      explanatory comments, never in a @source tag or a Gherkin step. Tag audit confirms
      @source:probe-* count is 0 across all four case files. Both scenarios now carry
      @source:assumed with [ASSUMED — needs verification] and a note that
      tools/prober.py implements P1–P5 only.
  - id: B2
    status: FIXED
    verification: >
      The "API totalCount" assertion is gone from happy-path.md's steps. It was not
      silently dropped — _feature.md now carries a "Blocked on the API oracle" section
      naming the requirement (filter-inventory.md §3), the blocker (oracle.py unbuilt,
      MITM_ENABLED=false), and the unblock condition. Parking a blocked requirement
      where someone can find it is better than deleting it.
  - id: B3
    status: FIXED
    verification: >
      "works correctly after rotating" → "An entered minimum survives device rotation",
      asserting the field retains 80,000 and Apply stays reachable. Both are observable.
      The case was kept rather than deleted, which is the right call — an EditText losing
      its value on configuration change is a real defect class.
  - id: B4
    status: FIXED
    verification: >
      Now "Then no listing priced above 120,000 appears in the results" — the relational
      form already used correctly elsewhere in the set. Falsifiable by inspection.
  - id: B5
    status: FIXED, plus an unflagged issue found and fixed
    verification: >
      The listing at the bound is now a Given precondition established from unfiltered
      results and skipped if unmet (edge-cases.md:14), not a Then asserting live
      inventory. Confirmed by reading the scenario: the assertion is "that listing still
      appears", which is relational to the precondition.
      Separately, the writer noticed and fixed something this audit missed in cycle 1:
      the scenario used "Dubai Marina", a real brokerage's live inventory, where
      docs/GUARDRAILS.md §3 and tests/test_data.py mandate the sanctioned test location.
      That is a production-safety issue and should have been a cycle-1 blocking item.

advisory:
  - id: A1
    status: DECLINED — accepted
    note: >
      Writer declined the split, arguing the four assertions are one behaviour ("the
      sheet opens with its documented defaults") and that splitting produces three
      near-identical scenarios differing only in which default they read. That is a
      correct reading of the format rules, which prohibit exactly that copy-paste
      pattern. Declining with a rationale is what the protocol allows; the rationale
      holds.
  - id: A2
    status: FIXED
    note: >
      coverage.md's Outline now states the Examples block is a 5-row sample and the
      30-row array is the source of truth.
  - id: A3
    status: DEFERRED — correctly
    note: >
      E2 (full filters sheet) remains under-covered: 8 of 30 array rows use it, one
      scenario tests it, and that scenario only asserts the section is present. Fixing it
      needs a new scenario, which the revision protocol forbids mid-revision for an
      advisory item. Recorded as a declared gap in _feature.md for the next writing pass.
      This is the protocol working, not a gap being ignored.
  - id: A4
    status: NEW — advisory only
    file: coverage.md
    issue: >
      The band definitions table ("mid = 80,000–120,000 for Rent Yearly") is marked
      [ASSUMED — needs verification] and is plausible for Dubai, but Al Napoca is the
      sanctioned test location and its price distribution is unknown. Bands chosen for
      Dubai may return zero results everywhere in Al Napoca, which would make most
      coverage rows vacuously pass.
    suggestion: >
      Before executing the array, read the unfiltered Al Napoca result set once and set
      the bands from its actual spread. This does not block — a vacuous pass is visible
      as an empty result set during execution — but it would waste a run.

coverage_gaps:
  - "E2 full-filters-sheet under-covered (A3) — now declared in _feature.md."
  - "Price slider (view_range_bar) untested; text entry and slider entry may disagree."
  - "Clear/reset of an applied range untested."
  - "E3 deep-link entry: BAYUT_DEEPLINK_SCHEME blank, nothing can exercise it. Building it would make several boundary cases deterministically executable."
  - "E4 push-notification landing: no case, no tooling."

stats:
  scenarios: 21
  with_cited_source: 5          # @source:observed — all five citations opened and verified
  assumed_unverified: 16        # explicitly marked; acceptable under the gate
  fabricated_source: 0          # was 2 in cycle 1
  scenarios_without_any_source: 0
  blocking_items: 0
  advisory_items: 4             # A1 declined, A2 fixed, A3 deferred, A4 new
  scenario_count_change: "21 → 21 (no growth during revision, per protocol)"
```

---

## Gate

`PASS` requires zero blocking items **and** every expected result either cited or
explicitly marked `[ASSUMED — needs verification]`.

- Blocking items: **0**
- Scenarios: **21**; source lines: **21**; scenarios with no source: **0**
- Fabricated citations: **0** (was 2)
- All 5 `@source:observed` citations re-opened and verified: page sources
  `en-GB-737ce49f1ddb.xml` and `en-GB-200fe0593bc8.xml` exist and say what is claimed;
  `price_range_sheet.py::apply()` exists; `test_price_range_picker` exists and passes.

Verdict is `PASS_WITH_NOTES` rather than `PASS` solely because of the four advisories,
none of which block execution.

---

## Auditor's note

**16 of 21 scenarios are `[ASSUMED — needs verification]`.** That ratio is the honest
state of this feature, not a defect in the case set: no probe has ever been run against
this app, so nothing about what the price filter *does* is known. A case set claiming
otherwise would be the failure mode this loop exists to catch — and in cycle 1, two
scenarios did exactly that.

**The thing worth carrying to the next feature:** the writer found a production-safety
issue during revision that this audit missed in cycle 1 — a scenario searching "Dubai
Marina", a real brokerage's live inventory, against `docs/GUARDRAILS.md` §3. Check C
should include a sanctioned-test-data check, not just coverage. That is a fix to
`.claude/agents/test-case-auditor.md`, not to this case set.

**On the loop itself:** it converged in 2 cycles of a permitted 3, with no disputes. The
one declined advisory (A1) was declined with a rationale that holds, which is the
protocol working as intended — a writer that had silently complied would have produced
three copy-pasted scenarios and a worse case set.
