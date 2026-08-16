---
name: design-test-cases
description: Designs a complete manual test case suite for a new or modified feature in any of the group's native iOS and Android apps — Bayut UAE, Bayut KSA, Bayut Egypt, Bayut GCC, Dubizzle Egypt, Dubizzle GCC, Zameen PK, OLX PK, or Hatla2ee — working from whatever raw inputs exist, whether a BRD, a ticket, Figma links, an events or tracking sheet, or pasted conversation, and optionally uploads the finished suite to Testmo. Also handles the review side of the same work: taking an existing Testmo suite through a live reviewer-comment cycle, case by case, applying corrections, flagging ambiguity, and trimming the suite afterward. Use this skill whenever someone asks for test cases, a test suite, test scenarios, QA coverage, a test plan, or a testing checklist for a mobile app feature; when they paste a ticket description, BRD, or requirements doc and ask what to test; or when they paste an existing case plus reviewer comments and ask for the case to be updated. Use it even when the request is casual ("what should we test for this?") or when only a ticket link is supplied. Do not use it for web app test cases or for writing automation code.
---

# Designing mobile app test cases

This skill produces manual test cases for the group's native iOS and Android apps, in the house style the QA team uses in Testmo. It is for mobile only — never produce web-specific cases (browser compatibility, responsive breakpoints, cross-browser rendering).

The workflow is the same for every app. What differs per app — languages, screen vocabulary, device matrix, deeplink domains, Testmo project — lives in an app knowledge base, loaded in Phase 0.

**Two different jobs share this skill.** Phases 0–9 below are for designing a suite from
nothing. If a suite already exists in Testmo and the task is applying live reviewer
comments to it case by case, or trimming/consolidating an existing suite — a different
shape of work with its own failure modes — go to
`references/reviewing-existing-suites.md` instead. It assumes the house style and
knowledge-base conventions below; it doesn't repeat them.

## Before you start

Read these three files, in this order. They are short and they change how you write every case:

1. `references/writing-rules.md` — the house style. Non-negotiable, and identical across all apps.
2. `references/common-scenarios.md` — the mandatory cross-cutting scenarios that go into every suite.
3. `references/learnings.md` — accumulated group-wide corrections. These override the other two where they conflict, because they are the most recent thinking.

Read `references/testmo-mapping.md` only at the upload step, and the app knowledge base in Phase 0. Read `references/reviewing-existing-suites.md` only when the task is reviewing an existing suite, not designing a new one — see above.

## Phase 0 — Identify the app and load its knowledge base

Every suite targets exactly one app. Read `references/apps/_index.md`, pick the right knowledge base, and read **only that one — in full**.

The knowledge base supplies what the app is, its language set, screen and domain vocabulary, core user journeys, known fragile areas, device matrix, deeplink domains, minimum OS versions, analytics and remote config conventions, and the Testmo project. Without it you will write cases in the wrong vocabulary against the wrong languages, and miss the app's known regression-critical areas. Section 6 (fragile areas) and section 4 (core journeys) in particular tell you where a new feature needs extra coverage.

If the app is not stated and cannot be inferred from the inputs, ask. Do not default to Bayut UAE because its knowledge base is the most complete. Watch the app's domain — property, classifieds, or automotive — because it sets the vocabulary.

Most knowledge bases are stubs with `TODO` or *(unconfirmed)* fields. **Never fill a gap with a guess.** A confidently wrong language set or OS floor produces cases that look authoritative and send testers down the wrong path. Ask for the value, design around the gap, and offer to record the answer via the `update-knowledge` skill afterwards.

If the feature ships to several apps, design against the primary app and add a per-app delta covering only what differs. Do not regenerate the whole suite per app.

## Phase 1 — Intake

The person will hand you some mix of: a BRD or ticket description, a ticket ID or link, Figma links, an events/tracking sheet, localisation sheets, conversation excerpts, or screenshots. Rarely all of them. Sometimes just one.

**Check which tools you actually have before promising anything.** Connectors are not available on every plan, and a teammate on the free plan will typically have none of them. The skill must work either way.

*If the relevant connector is available:*

- **Ticket system (ClickUp)** — fetch the **complete** ticket: description, custom fields, attachments, and checklists. Then fetch the **comments** separately — they frequently contain the product Q&A that resolves ambiguity in the description. Download and view attached images rather than assuming what they show.
- **Figma** — pull the design context, screenshots, and metadata for every relevant screen and state. Use it for exact copy strings, component states, and the empty/error/loading states the BRD forgot. **If Figma access is blocked, stop and say so** — ask the person to share the file with the connected account. Never fabricate design behaviour.
- **Drive / Sheets** — fetch events docs, tracking sheets, and localisation sheets, and use the real event names and parameters rather than writing "as per the tracking sheet" and moving on.
- **Chat** — read referenced threads for decisions made after the BRD was written.

**Read both the ticket and its linked design before designing anything.** A suite built from the ticket alone reliably misses states that exist only in the design.

*If it is not available, or a fetch fails:*

Say so plainly and ask the person to paste the content instead. Name exactly what you need and why — "paste the ticket description and any comments that answer open questions", "paste the rows of the tracking sheet covering this feature", "paste the localised strings, or tell me which languages ship". Then continue from what they give you.

Never invent the contents of something you could not read, and never quietly skip an input.

## Phase 2 — Build a requirements ledger

Before writing a single test case, extract every testable statement into a numbered ledger. Pull from:

- The scope of work and implementation details
- Every acceptance criterion
- Answered questions in the Q&A section (these are requirements)
- Exact copy strings, character limits, and numeric thresholds
- Remote config flag names and their default values
- Named analytics events and their parameters
- Anything explicitly declared out of scope or unchanged (these become regression cases)

This ledger is what you trace coverage against in Phase 5. Keep it — you will need it.

## Phase 3 — Clarify first (hard rule)

**Never guess on ambiguity.** If the ticket, acceptance criteria, design, or copy are unclear, incomplete, or contradictory, stop and ask targeted questions before generating cases. Do not invent UI behaviour, and do not silently "fix" what looks like a bug in the spec — surface it as a question.

Things that always warrant asking: an undefined trigger or timing, a missing state, unclear error or empty behaviour, missing localised copy, contradictory acceptance criteria, or an unconfirmed target folder.

Separate what you find:

- **Blocking** — the answer changes what the correct behaviour is, so a test case written now might assert the wrong thing. Ask the person before designing that area.
- **Non-blocking** — write the case against the most defensible reading and mark it clearly so the reviewer sees the assumption.

Real example from the DPV survey BRD: "the spec says radio buttons but permits multiple selections" is blocking, because it determines whether multi-select cases are valid at all. "Do all lead types qualify?" is non-blocking — write a case covering the lead types the app supports and flag it.

Ask blocking questions in one batch. Do not ask them one at a time.

## Phase 4 — Design the feature-specific cases

**Every case has three mandatory fields**: Name/Summary, Description, and Expected Result. A case missing any of them is not finished. `references/writing-rules.md` specifies what goes in each — read it before writing, not after.

The short version:

- **Name** — one `Verify ...` sentence.
- **Description** — a **Gherkin scenario**: Given (preconditions) / When (actions) / Then (outcomes), with `And` continuing the preceding clause type. This is parsed into Testmo BDD steps on upload, so the keywords must be present and correctly ordered.
- **Expected Result** — numbered observable assertions that elaborate the Then clauses, **in the same order as the Then clauses**, because they are paired positionally on upload.

One logical behaviour per case. A second `When` after a `Then` means two behaviours — split it.

Work through the feature in this order. Skip any section that does not apply; do not pad.

1. **Trigger and gating** — what causes the feature to appear, and what suppresses it. Include the remote config flag both enabled and disabled.
2. **Content and static UI** — exact question text, option labels, button copy, placeholder text. Assert the actual string, quoted.
3. **Interaction** — selection, input, navigation, dismissal.
4. **Input validation** — minimum and maximum lengths, empty states, disabled/enabled control transitions. Cover the boundaries: one below the minimum, exactly the minimum, exactly the maximum, one above the maximum.
5. **Submission and dismissal** — both the happy path and abandoning the flow.
6. **Frequency, cooldown, and de-duplication** — anything with a time window or a "show once" rule. Cover inside the window, at the boundary, and after it elapses.
7. **State persistence and app lifecycle** — background/foreground, app kill and relaunch, logout and login, fresh install.
8. **Runtime config changes** — toggling a remote config flag while the app is running.
9. **Error and failure paths** — API failure, timeout, the triggering action itself failing.
10. **Cross-context edge cases** — the interesting ones. Where the trigger and the display are separated in time or context, write a case for every combination that produces different data. The DPV survey's Sale-lead-shown-on-Rent-DPV case is the model here.
11. **Regression on untouched behaviour** — anything the BRD says must remain unchanged. The DPV survey BRD said the rating & reviews nudge behaviour must be unchanged; that is a test case.

## Phase 5 — Append the cross-cutting scenarios

Add the mandatory scenarios from `references/common-scenarios.md`. Two rules:

**Tailor them.** A generic "Verify the feature on iPad as well" is a bad test case — it tells the tester nothing about what to look at. Name the specific surface: "Verify the survey UI/layout is displayed correctly on iPad and mini-screen iOS devices."

**Drop what does not apply.** If the feature has no deeplink entry point, there is no deeplink case. Say which ones you dropped and why, so the reviewer can push back.

## Phase 6 — Self-review

Do this before showing anything. Check every case against:

- **All three fields present.** No case ships with an empty Description or Expected Result. This is the check that fails most often when working at speed.
- **Expected Results are falsifiable.** Scan for "works correctly", "as expected", "as per requirements", "behaves properly". Each one is a case that can never fail. Replace with something observable.
- **Valid Gherkin.** Every Description has at least one Given, one When, and one Then. No scenario starts with `And`. No `When` appears after a `Then` — that is two behaviours in one case.
- **Assertion order matches Then order.** Expected Result item 1 corresponds to the first Then, item 2 to the next Then/And, and so on. They are paired positionally on upload, so mismatched order produces wrong Testmo steps.
- **No assertions hiding in Given or When.** "When the user taps Submit and the sheet dismisses" — the dismissal is a Then.
- **No Description that restates the Name.** The three fields are different zoom levels, not three phrasings of one sentence.
- **Preconditions are complete.** Every case that depends on a remote config value, cooldown state, auth state, language, or specific device says so. Unstated preconditions are the main cause of non-reproducible results.
- **Duplicates.** Compare cases pairwise for semantic equivalence, not just identical text. This is a real and recurring failure — the shipped DPV survey suite contains two byte-identical cases (2363656 and 2363657). Catch it here.
- **Atomicity.** One case, one verifiable behaviour. If the Steps contain a branch ("if X do this, otherwise that"), split the case. Independent assertions become separate cases; consequential ones become separate numbered lines in a single Expected Result.
- **Standalone readability.** Never write "verify all the above cases" or "same as above". Order is not preserved once cases are in Testmo, so a case that depends on its neighbours is broken. Expand it.
- **Style.** Every case matches `references/writing-rules.md`.
- **Coverage trace.** Every numbered item in the Phase 2 ledger maps to at least one case. Report any that do not, with a reason.

## Phase 7 — Report, don't recite

**Do not print the test cases in the response.** A 40-case suite dumped into chat is unreadable, burns the session, and nobody reviews it there — the spreadsheet is where review happens.

Report only:

- **Count and shape** — how many cases, broken down by section.
- **Coverage** — every numbered item in the Phase 2 ledger is covered, plus any that are not and why.
- **Assumptions made** — every non-blocking gap you wrote through.
- **Cross-cutting scenarios dropped** — with reasons.
- **Open questions** — anything still blocking.

Keep it to a short summary the person can scan in a few seconds. If they ask to see specific cases — "show me the cooldown ones" — show those, and only those.

## Phase 8 — Produce the deliverable

**The export is the only deliverable at this stage.** Do not write a JSON file; the upload skill generates its own from the reviewed export when the time comes. One artefact, no chance of the two drifting apart.

**Default to CSV** — the flat, one-row-per-case format for direct Testmo import:

```
python scripts/sheet_tools.py export --out "<Feature> Test Cases.csv"
```

Same ten columns as always (`#, Section, Test Case, Description (BDD), Expected Result,
Notes, QA Status (Android), QA Status (iOS), Comments, Testmo Case ID`), Section repeated
on every row, no banner rows, no styling — needs no dependency beyond the standard
library. Format is inferred from `--out`'s extension.

If the deliverable is for human review first (Notion, Google Sheets) rather than direct
import, use xlsx instead — same columns, but with section banner rows, per-platform QA
status dropdowns, and a **Summary** sheet whose pass/fail counts are formulas that update
as QA fills the status columns:

```
python scripts/sheet_tools.py export --out "<Feature> Test Cases.xlsx" --app "<App>"
```

Hand over the file and say what happens next: review (Notion, or directly in the CSV),
corrections, then upload.

## Phase 9 — Hand off for review

**Review is a manual step, and it comes before Testmo.** Do not upload anything from this skill.

The current process: the finished spreadsheet goes to the team's **Notion** repository, where a reviewer works through it and records corrections. The sheet is the single source of truth from here — there is no JSON copy to keep in sync.

When a reviewed sheet comes back:

- If the corrections are **case-level fixes**, apply them to the sheet and regenerate.
- If a correction is a **generalisable rule** — something that should change how every future suite is designed — route it through the `update-knowledge` skill so the next design already knows. This is the step teams skip, and skipping it means the same correction gets made again next month.

Uploading the approved sheet to Testmo is the `upload-to-testmo` skill's job. Mention it exists; do not invoke it as part of designing.

**Why the separation matters:** Testmo has no update or delete API. Every uploaded case is permanent, and a mistake can only be fixed by hand in the Testmo UI. Review before upload is the only cheap place to catch problems.

## Working in a constrained session

Some of the team is on plans with tight message limits and no connectors. A 40-case suite can exhaust a session before it is finished. When that is the situation:

- **Ask up front how they want to work it.** Whole suite in one pass, or section by section.
- **Section by section is the safer default under a limit.** Deliver Phase 4's sections one at a time, each complete with all three fields, and keep a running list of which sections remain. Each response should stand on its own so a session that ends early still leaves usable output.
- **Front-load the requirements ledger.** If the session runs out, the ledger plus a partial suite is far more useful to pick up from than a full suite of thin cases.
- **Do not pad.** Skip the narration, skip restating the BRD back, go straight to cases.
- **Write the spreadsheet as you go**, appending each section, so the artefact survives even if the conversation does not.
