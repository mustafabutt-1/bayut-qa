# Accumulated learnings

Team corrections captured over time. Newest at the top. These override `writing-rules.md` and `common-scenarios.md` where they conflict, because they represent the most recent thinking.

**Entry format** — keep it exact, so entries stay greppable and consolidatable:

```
## L-NNN — Short title
**Date:** YYYY-MM-DD
**Captured from:** where this came from (feature, review, incident)
**Rule:** the instruction, in imperative form
**Why:** the reasoning, so a future reader can tell when it stops applying
**Example:** a concrete before/after where useful
```

Do not edit or delete past entries. If a rule is superseded, add a new entry that says so and reference the old ID.

---

## L-013 — Check for a bucket-forcing mechanism before writing a single case for an A/B feature
**Date:** 2026-08-17
**Captured from:** Recently Viewed Properties review (Bayut UAE)
**Rule:** When a feature is gated by an A/B experiment, before writing any case whose `Given` assumes a specific bucket, confirm there is a documented way to force a test account into that bucket. If there isn't, don't write 80 cases that all silently assume it — flag the gap once, up front.
**Why:** In this suite, every one of ~80 cases opened with "Given the test user is assigned to the `X` experiment group," and no case, comment, or doc anywhere stated how a tester actually gets into that state. Found only on a full-suite audit at the end, by which point it was a systemic finding instead of a five-minute check at the start.

## L-012 — A suite pulled twice mid-review is how you catch "applied" vs. "actually applied"
**Date:** 2026-08-17
**Captured from:** Recently Viewed Properties review (Bayut UAE)
**Rule:** When told a batch of fixes has been applied to a live Testmo suite, re-pull the export and diff it against what was actually requested — don't take a verbal "done" at face value when case content matters.
**Why:** In this cycle, one fix landed with a duplicated line instead of a clean replacement, and a separate agreed case retirement never actually happened, despite both being reported as complete. Neither would have been caught without re-pulling and reading the actual export.

## L-011 — Recognise premise reversal before editing a case
**Date:** 2026-08-17
**Captured from:** Recently Viewed Properties review (Bayut UAE)
**Rule:** When a review comment contradicts a case's core `Then` rather than refining it, rewrite the whole scenario. Patching the disputed clause alone leaves every downstream clause built on the now-false premise unchanged and wrong.
**Why:** Two cases in this cycle had comments stating the exact opposite of what the case asserted (a sign-in gate that didn't actually exist; a cached carousel shown offline when actually a message replaces it entirely). Editing just the flagged line would have left the rest of the scenario internally inconsistent.
**Example:** See `reviewing-existing-suites.md`'s "Recognise a premise reversal" section for the full before/after.

## L-010 — Ambiguous review comments get flagged back, not resolved by pattern-matching the last similar one
**Date:** 2026-08-17
**Captured from:** Recently Viewed Properties review (Bayut UAE)
**Rule:** An ambiguous comment ("this line doesn't make sense," no replacement given) is not resolved by guessing based on how a similarly-worded comment was handled elsewhere. Check whether the confirmed-fact base already settles it; if it doesn't, ask, and say plainly which reading you'd default to and why — but don't silently commit to one in the case text.
**Why:** This is `L-009` sharpened by a specific failure mode: two comments in the same review thread used near-identical wording ("this doesn't make sense") for two different underlying problems, and the same fix would have been wrong for at least one of them. Full methodology in `reviewing-existing-suites.md`.

## L-005 — Every case carries three fields
**Date:** 2026-07-26
**Captured from:** Testmo field mapping requirement
**Rule:** Never produce a case with only a title. Name/Summary, Description (preconditions + numbered steps), and Expected Result (numbered observable assertions) are all mandatory, because all three map to Testmo fields on upload.
**Why:** A title-only case forces the tester back to the BRD to work out setup and pass criteria, which is where interpretation drift starts. It also cannot be uploaded without leaving Testmo fields blank.

## L-009 — Never guess on ambiguity; ask before designing
**Date:** 2026-08-10
**Captured from:** QA Testmo agent prompt (colleague)
**Rule:** If the ticket, acceptance criteria, design, or copy are unclear, incomplete, or contradictory, stop and ask targeted questions before generating cases. Do not invent UI behaviour, and do not silently "fix" what looks like a spec bug — surface it as a question.
**Why:** An invented behaviour becomes a test case, the case becomes a bug report against correct code, and the tester loses a cycle. Asking costs one message.

## L-008 — Read the ticket AND the linked design before designing
**Date:** 2026-08-10
**Captured from:** QA Testmo agent prompt (colleague)
**Rule:** Fetch the full ticket (description, custom fields, attachments, checklists) and its comments, and open the linked Figma. If Figma access is blocked, stop and ask for access rather than proceeding.
**Why:** Empty, error, and loading states usually exist only in the design; a suite built from the ticket alone reliably misses them. Comments carry the product Q&A that resolves ambiguity in the description.

## L-007 — Testmo creates are permanent; review before upload
**Date:** 2026-08-10
**Captured from:** QA Testmo agent prompt (colleague) — corrects an earlier wrong assumption
**Rule:** Treat every Testmo upload as irreversible. There is no update and no delete API (`PATCH`/`PUT`/`DELETE` all 404). Confirm project, folder, and count explicitly before executing, and never send DELETE to a collection endpoint.
**Why:** An earlier version of this knowledge base claimed a sheet could be edited and "re-synced" to Testmo via the Case ID column. That is false. The Case ID column is a record of what was uploaded, nothing more, and a mistake can only be fixed by hand in the Testmo UI. This is why review moved ahead of upload as a separate manual gate.

## L-006 — Expected Results must be falsifiable
**Date:** 2026-07-26
**Captured from:** Testmo field mapping requirement
**Rule:** Ban "works as expected", "behaves correctly", "as per requirements" and equivalents from the Expected Result. State what is observable: a specific string, a specific UI state, a specific event with specific parameters, or a specific absence.
**Why:** A case that cannot fail reports as passed forever and provides zero coverage while appearing in the coverage numbers. This is worse than having no case, because it hides the gap.
**Example:** Not `The survey submits successfully.` but `The bottom sheet dismisses and the `dpv_survey_submit` event fires once with `purpose = Sale`.`

## L-004 — Assert the persisted value, not the displayed context
**Date:** 2026-07-26
**Captured from:** DPV In-App Survey (seed)
**Rule:** When a feature persists state at one moment and renders it at another, write an explicit case asserting that the reported value comes from the persisted record rather than the current screen. Cover both directions.
**Why:** This is the highest-value bug class in deferred-display features and it is invisible in a normal happy-path run. The DPV survey sends `purpose = Sale` even when the sheet renders on a Rent DPV, because purpose is read from the pending-survey record.
**Example:** `Verify the survey is displayed on the Rent DPV after generating a qualifying lead on the Sale DPV, closing the app, and reopening the Rent DPV, while the analytics event sends the original purpose as Sale and vice versa.`

## L-003 — Treat answered BRD questions as requirements
**Date:** 2026-07-26
**Captured from:** DPV In-App Survey (seed)
**Rule:** Parse the Questions and Product Q&A sections of a BRD and pull every answered item into the requirements ledger. Answers there frequently contradict or tighten the scope section above them.
**Why:** The DPV survey scope section did not state the cooldown anchor or the remote config launch default; both were only settled in the Q&A ("On survey display", "False"). A suite built from the scope section alone would have tested the wrong cooldown behaviour.

## L-002 — Cover the boundary in three cases, not one
**Date:** 2026-07-26
**Captured from:** DPV In-App Survey (seed)
**Rule:** For any numeric limit, write below-minimum, valid-range-including-both-ends, and above-maximum as separate cases. For any time window, write inside-window, at-boundary, and after-elapsed.
**Why:** Off-by-one and inclusive/exclusive errors are the most common defects in validation and cooldown logic, and a single "verify the limit works" case will not surface them.

## L-001 — De-duplicate semantically before submitting
**Date:** 2026-07-26
**Captured from:** DPV In-App Survey (seed)
**Rule:** In Phase 6, compare every case against every other for equivalent meaning, not just identical text. Report and remove duplicates before presenting.
**Why:** The shipped DPV survey suite contains two byte-identical cases (2363656 and 2363657). Duplicates either waste an execution cycle or get skipped, which silently reduces real coverage below reported coverage.
