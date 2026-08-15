# Recently Viewed Properties — why this exists, and how it's being worked

This directory is manual/Testmo test-case design work for the **Recently Viewed
Properties** homepage carousel (Bayut UAE) — a feature outside the automated
QA-agent framework this repo otherwise builds. It uses the separately-installed
`design-test-cases` Claude Code skill (`.claude/skills/design-test-cases/`), not the
`feature-test-designer`/`test-case-auditor` agent pair — that pair produces BDD cases
for *this repo's own* Appium suite (see `test-cases/price-filter/` for that format);
this feature needs manual Testmo cases for the QA team to execute by hand, in a
specific CSV shape they already use (see [[testcase-csv-format]] in memory).

## Why

The QA team supplied their own existing 78-case CSV for this feature and asked for
two things: an audit (duplicate/generic/irrelevant-case check against the
`design-test-cases` skill's own house style — `writing-rules.md`,
`common-scenarios.md`, `learnings.md` — and against `references/apps/bayut-uae.md`'s
confirmed facts), and then a from-scratch judgment call on how many of those cases
were actually worth keeping. That produced a finalized **79-case** baseline: the
original 78 minus nothing, plus one case split into two (an overloaded entry-point
case), with a handful of Name/Notes fixes for banned generic phrasing, an uncited
badge-type claim, and a low-confidence near-duplicate that turned out to be a
required third state on closer look, not a duplicate.

That baseline then went to the actual QA team for review in Testmo. This directory
tracks what came back.

## How

**Every CSV the QA team hands over is read in full before anything is done with
it** — the original 78-case baseline, and any future replacement or supplementary
CSV, gets opened and read end to end, not sampled from the header row or the first
few cases and generalized from there. This is the same "evidence over inference"
discipline the automated agent pipeline enforces (CLAUDE.md hard rule) applied to
this manual workstream: a case count, a section list, or a "this looks fine" verdict
is only as good as whether every row was actually read, and the two data-integrity
bugs below were only caught because re-reads happened, not because the tooling
guaranteed correctness on its own.

**The review comments are being applied incrementally to a JSON working file, not
to the CSV directly**, and the CSV is *not* being re-exported after every comment —
the QA team is working through the suite case-by-case and asked explicitly not to
regenerate until they say the whole pass is done. `modified-cases.md` in this
directory is regenerated straight from that JSON on request, so it's always an
accurate snapshot of current state without needing a CSV re-export to see it.

**Every review comment gets one of three treatments, no exceptions:**

1. **Clear and actionable** — applied directly (e.g. renaming "promotional banner
   carousel" to the team's actual term "Homepage banners," or adding a case for
   "contacted listings shouldn't reappear in Recently Viewed").
2. **Ambiguous** — flagged back to the reviewer instead of guessed at. Two review
   comments so far genuinely didn't specify what change was wanted (case 2's "this
   needs modification" without saying what, and case 5's "this line doesn't make
   sense" without saying what should replace it) — the first got resolved once a
   follow-up supplied the actual Remote Config spec table and the fix became
   inferrable with confidence; the second is still open. Guessing wrong on a case
   that's about to go into Testmo costs more than asking once.
3. **Contradictory** — surfaced explicitly, not silently resolved by picking one.
   One reviewer comment said the Home carousel needs 1 viewed property to appear;
   a later comment on a different case said it needs 3. That's a real conflict
   between two comments from the same reviewer thread, not something to average out
   or guess between — see `modified-cases.md`'s "Still open" section for exactly
   which cases are affected either way.

**Two data-integrity bugs were caught and fixed along the way, unrelated to review
content:** a hand-transcribed CSV row with an unquoted comma-containing title field
silently shifted every column after it (caught by reparsing after export, not
assumed correct from a first successful export); and a raw-text find/replace on the
CSV introduced unescaped commas into two `Notes` fields. Both were fixed by rebuilding
from the structured JSON rather than patching CSV text by hand, which is now the only
way edits happen — raw-text edits on the exported CSV are exactly how the first bug
happened, so that path is deliberately not used again.

**Durable corrections went to the skill's knowledge base, not just this suite.**
"Homepage banners" is now recorded in `references/apps/bayut-uae.md`'s vocabulary
table and as learning `UAE-001`, so the next suite designed for this app gets the
team's real terminology on the first pass instead of needing the same correction
again.

## Where things stand

See `modified-cases.md` for the full list of changed and newly-added cases. Nothing
has been exported to a final CSV since review comments started — that happens once
the QA team confirms the pass is complete. The working JSON is not checked into this
repo (it's a scratch/session file); if a CSV is wanted as a durable artifact before
that point, ask and one will be generated and committed.
