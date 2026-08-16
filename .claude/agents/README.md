# Agents — index and status

Agent definitions live in this directory as `<name>.md` with YAML frontmatter
(`name`, `description`, `tools`) and a body containing inputs, step-by-step procedure,
output format, and hard rules. They are runbooks, not one-paragraph descriptions.

**Status is honest here.** One agent is written. Twelve are specified but not built —
listed below so nobody assumes a missing file means a forgotten requirement.

---

## Built

| Agent | File | What it does |
|---|---|---|
| **app-cartographer** | [`app-cartographer.md`](app-cartographer.md) | Builds the context pack by driving the live app. **PASSIVE** mode crawls and inventories screens, elements and accessibility ids. **PROBE** mode manipulates filters and reads result counts to determine behavioural rules. Runs before Phase 1 and re-runs per build to detect drift. |
| **feature-test-designer** | [`feature-test-designer.md`](feature-test-designer.md) | Turns a feature name / ticket / screen into a BDD case set under `test-cases/<slug>/`. Establishes the feature's mapping state from `context/`, enumerates entry points from the screen graph, probes what the app can answer, and calls `tools/pairwise.py` for combinatorial coverage. **Writes and revises; never self-approves.** |
| **test-case-auditor** | [`test-case-auditor.md`](test-case-auditor.md) | Judges a case set without seeing the writer's reasoning. Opens every cited source to check it says what the case claims. Emits a machine-readable verdict to `_audit.md`. **Judges only; never edits cases.** |
| **testmo-suite-designer** | [`testmo-suite-designer.md`](testmo-suite-designer.md) | A separate lineage from the three above — wraps the `design-test-cases` skill (manual Testmo suites, not this repo's automated BDD suites). DESIGN mode builds a suite from a PRD/Figma/remote-config/tracking-sheet mix; REVIEW mode takes an existing Testmo suite through a live reviewer-comment cycle, case by case, and can trim/consolidate it afterward. Grew out of a real 82-case Bayut UAE review cycle; the comment-triage and reduction discipline it follows lives in `design-test-cases/references/reviewing-existing-suites.md`. **Never uploads to Testmo.** |

`app-cartographer` is the only agent that writes to `context/`. Everything else reads it.
`testmo-suite-designer` writes to the `design-test-cases` skill's app knowledge bases via
`update-knowledge`, not to `context/` — it works one layer above the app-crawl pipeline
the other three agents share.

### The write–audit–revise loop

`feature-test-designer` and `test-case-auditor` are a **pair**, not two independent
agents. A single-pass generator produces plausible-looking cases with subtly wrong
expected results, and nobody notices until the suite has been running a month.

```
writer produces → auditor judges → FAIL? writer revises by item id → re-audit
```

Termination is bounded, and enforced in both specs:

- **Max 3 cycles.** Cycle 3 without a `PASS` → `verdict: ESCALATE`, a human decides.
- **The writer may dispute** a blocking item with counter-evidence and mark it
  `DISPUTED` — that escalates immediately, no further cycles. Auditors are wrong
  sometimes, and a writer that silently obeys a wrong objection corrupts the case set.
- **No new scenarios during revision** unless a blocking item demands one. Revision
  cycles that grow the case set never converge.
- Every cycle is logged to `_audit-history.md`, so a *pattern* of failures across
  features is visible — and a recurring pattern is a fix to the agent spec, not to the
  individual case set.

**Reference run:** [`test-cases/price-filter/`](../../test-cases/price-filter/) — a real
two-cycle loop. Cycle 1 `FAIL` on 5 blocking items (including two scenarios citing a
probe `P6` that does not exist, with a fabricated date and build number); cycle 2
`PASS_WITH_NOTES`. `_audit-history.md` records both, plus the two spec fixes the loop
surfaced about itself.

---

## Specified, not yet built

### Prevent

| Agent | Input → Output |
|---|---|
| `requirements-adversary` | ClickUp ticket + AC + Figma → ambiguities, missing states, error/empty/offline cases, RTL implications, test charter |
| `test-designer` | charter + `filter-inventory.md` → calls `pairwise.py` for the covering array → drafts cases with expected results → pushes to Testmo as **drafts**. **Largely superseded by `feature-test-designer` + `test-case-auditor` above**, which cover everything except the Testmo push. What remains unbuilt is the push itself, which needs `tools/testmo_client.py`. Reconcile the two rather than building a third generator. |

### Build

| Agent | Input → Output |
|---|---|
| `locator-cartographer` | crawl output → screen objects + a report of elements lacking stable ids (**note:** overlaps `app-cartographer`; reconcile the two before building, rather than shipping two crawlers) |
| `flow-builder` | Testmo case + `element-inventory.json` → Appium test. Prefers deep links and API seeding over UI navigation for setup steps |

### Execute

| Agent | Input → Output |
|---|---|
| `regression-scoper` | release notes + sprint tickets + historical defect density → risk-weighted subset of the 144 cases |
| `run-orchestrator` | device provisioning, parallel execution, artifact capture, Testmo result posting |
| **`failure-triage`** | screenshot + page source + logcat + HAR + retry outcome → **REAL DEFECT / TEST DEFECT / LOCATOR DRIFT / ENVIRONMENT / DATA / FLAKE**, with the decision rules written as an explicit table. **This agent decides whether the programme survives — it gets the most rigorous spec of the set.** |
| `bug-report-writer` | REAL DEFECT → complete `.md` from `templates/BUG-TEMPLATE.md`: embedded screenshots, trimmed logcat, API evidence, human-executable repro steps, unchecked verification checklist. **Never files a ticket.** |
| `self-healer` | LOCATOR DRIFT → re-dump page source → propose a locator diff for review. **Never auto-merges.** |

### Continuous

| Agent | Input → Output |
|---|---|
| `production-signal` | Crashlytics + store reviews + support tickets → cluster → rank by user impact → repro attempt → report |
| `suite-curator` | audit Testmo against the app: stale cases, duplicates, coverage gaps by feature area, new cases drafted from confirmed defects |
| `control-tower` | daily run summary, defect trends, flake rate, coverage heatmap, release-readiness call. Plain text, suitable for direct send to Ted |

---

## The chain

```
app-cartographer ──→ context/ ──→ everything else

requirements-adversary → test-designer → Testmo drafts → flow-builder → pytest suite
                                                                            │
regression-scoper → run-orchestrator ───────────────────────────────────────┘
                              │
                           failure
                              │
                      failure-triage
                     ┌────────┼─────────────┬──────────────┐
                     ▼        ▼             ▼              ▼
              REAL DEFECT  TEST DEFECT  LOCATOR DRIFT   FLAKE / ENV / DATA
                     │        │             │              │
          bug-report-writer   │        self-healer     logged with evidence,
                     │   test-defect report  │         never silently dropped
                     ▼        ▼             ▼
              reports/*.md — unverified, awaiting human review
                              │
                     human files it in ClickUp
```

---

## Hard rules every agent inherits

These come from `CLAUDE.md` and are not restated in each agent file. They apply anyway.

1. **Never file a ticket.** Output is an unverified Markdown report in `reports/`.
2. **Evidence over inference.** No evidence → `UNKNOWN — needs manual verification`.
3. **Never read the app source.** `context/` is the only source of truth about the app.
4. **Never do combinatorics.** Call `pairwise.py`.
5. **If evidence contradicts the test's own assertion, produce a TEST DEFECT report, not
   a bug report.** Applies to `failure-triage` and `bug-report-writer` both. False
   positives cost credibility with dev exactly when it is needed most.
6. **Never tap outside the safety guard.** Any agent driving the device goes through
   `tools/crawl_safety.py`.

---

## Writing a new agent

- Frontmatter: `name`, `description` (written so the dispatcher can route to it),
  `tools` (least privilege — do not grant `Write` to an agent that only reads).
- Body: **Inputs** → **Procedure** (numbered, concrete) → **Output format** →
  **Hard rules**.
- Depth of a real runbook. If a step needs a decision, say what evidence settles it.
- Prefer calling a tool over reasoning. If an agent is doing arithmetic or set
  operations, that logic belongs in `tools/` instead (D-003).
- Every claim the agent writes must carry its evidence: the screenshot, the raw counts,
  the page-source fragment.
