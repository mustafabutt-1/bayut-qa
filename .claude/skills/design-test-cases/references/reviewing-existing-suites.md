# Reviewing an existing suite against live reviewer comments

`writing-rules.md` and the Phase 1–9 flow in `SKILL.md` cover **designing a suite from
scratch**. This file covers a related but distinct job: a suite already exists in Testmo,
a reviewer is working through it case-by-case leaving comments, and the task is to apply
those comments correctly — one at a time, as they arrive, often across many turns.

Derived from a real 82-case Testmo review cycle (Bayut UAE, Recently Viewed Properties,
2026-08). Every rule below has a concrete before/after from that cycle.

## Contents

- [The three comment types](#the-three-comment-types)
- [Verify before applying](#verify-before-applying)
- [Recognise a premise reversal](#recognise-a-premise-reversal)
- [Conflicting reviewer terminology](#conflicting-reviewer-terminology)
- [Cross-case consistency](#cross-case-consistency)
- [Reducing an existing suite](#reducing-an-existing-suite)
- [Testability triage vs. wording fixes](#testability-triage-vs-wording-fixes)
- [Format discoveries from real exports](#format-discoveries-from-real-exports)

## The three comment types

Every review comment is exactly one of these. Decide which before touching the case.

1. **Clear and actionable** — the comment states what's wrong and what should replace
   it. Apply directly. *Example: "Change the naming convention of homepage promotional
   banner to Homepage banners" — unambiguous, apply everywhere the term occurs.*
2. **Ambiguous** — the comment names a problem but not the fix. **Flag it back. Never
   guess.** Present the plausible readings and say which you'd default to and why, but do
   not silently commit to one in the case text if there's a real fork.
   *Example: a reviewer flagged a case's `When` clause as "irrelevant" with no
   replacement given. Two readings existed — drop the check entirely, or just simplify
   the wording — and they produced materially different cases. Guessed wrong once
   already elsewhere in the same cycle before adopting this rule.*
3. **Contradictory** — two comments (same reviewer or different reviewers) imply
   opposite things. **Surface the contradiction explicitly. Do not average or silently
   pick one.** Write down exactly which cases are affected either way, so whoever
   resolves it can see the blast radius.
   *Example: one comment said the feature's carousel needs only 1 viewed property to
   appear; a later comment on a different case said it needs 3. Both readings had
   already been applied to different cases by the time the contradiction was noticed —
   tracking "which cases assume which reading" was what made it fixable.*

## Verify before applying

Before resolving an ambiguous or contradictory comment, check whether the confirmed-fact
base (the app knowledge base, a regression checklist, an already-answered spec question
elsewhere in the same review thread) already settles it. Don't re-derive an answer by
guessing when it's already on record.

*Example: a reviewer asked "confirm whether the app retains local storage upon app
override" as an open question on one case. The regression checklist already stated this
explicitly for a different but related requirement — the answer was a citation, not a
guess. Recorded as `UAE-003` in the app knowledge base afterward specifically so this
doesn't need re-deriving next time.*

When you do resolve something new this way, write it into the app knowledge base
(`apps/<app>.md`, section G) as soon as it's confirmed — not just used once and
forgotten. See `update-knowledge` skill.

**Keep internal citations out of the case text.** A note like "confirmed by UAE-003" is
for your own reasoning and the person you're reporting to — it does not belong in a
`Given`/`Then` clause or an Expected Result line a tester will read. State the fact
plainly there instead.

## Recognise a premise reversal

Most comments refine a case. Some invalidate its entire premise — the reviewer is saying
the opposite of what the case currently asserts, not adding detail to it. Recognise the
difference before editing:

- **Refinement**: reword, add a precondition, tighten an assertion. Most of the Given/
  When/Then survives.
- **Reversal**: the comment states a fact that contradicts the case's core `Then`. Don't
  patch pieces — rewrite the whole scenario, because every downstream clause built on
  the old premise is now wrong too.

*Example: a case asserted "tapping the favourite heart while logged out opens a sign-in
screen." The comment was "this is contradictory to business logic — Bayut UAE allows
favouriting in logged-out state." Every clause after the sign-in assumption (sign-in
screen shown, favourite applied after sign-in, etc.) was invalidated at once — the fix
was a full rewrite, not an edit to one line.*

A useful tell: if applying the comment naturally would flip a `Then` clause to its
opposite, check whether everything *after* that clause in the scenario still makes sense
before touching anything.

## Conflicting reviewer terminology

Two reviewers sometimes give different naming corrections for the same thing, at
different points in the same cycle. Default to whatever's **already been applied
consistently** across the suite so far, not the most recent comment — a later switch
means revisiting every case already fixed. Flag the conflict rather than silently
picking either side; it's the kind of thing worth a thirty-second confirmation rather
than a guess that might need undoing across a dozen cases.

## Cross-case consistency

A fix applied to one case can silently contradict another case's premise, especially
when both touch the same underlying app state (network connectivity, a shared config
key, a shared UI element). After applying any comment, check: **does this case's new
`Given` or `Then` now conflict with any other case's stated behaviour for the same
condition?**

*Example: fixing one case to say "no internet connection → the carousel doesn't render
at all, a message shows instead" was correct for that case. A second, newly-added case
about tapping a card with no connection then needed its own `Given` corrected too — it
had been written assuming the carousel *could* be on screen with no connection at the
same time, which the first fix had just ruled out. Caught only by deliberately
re-checking cases that touch the same condition, not automatically.*

This is not a one-time check — re-run it any time a comment changes what a shared
condition (a config value, a permission state, a connectivity state) is defined to mean.

## Reducing an existing suite

When a suite has grown large through review (new cases added per comment, device/locale
combinations multiplying), distinguish real cuts from ones that would hide risk:

**Safe cuts — not a test-design tradeoff, just clutter:**
- A case that isn't actually executed against the app (a dashboard/log review dressed up
  as a Testmo case — e.g. "verify Crashlytics shows no new issues"). Belongs on a release
  checklist, not in the suite a tester runs case-by-case.
- A case whose title promises broad coverage ("verify all other X are unchanged") that
  duplicates, or is silently narrower than, dedicated cases that already exist for the
  specific things adjacent to the feature.

**Merge candidates — real coverage, thin distinction, worth a judgment call:**
- Two cases proving the *same underlying invariant* via two different triggers (e.g.
  "state survives backgrounding" and "state survives a call/notification interrupt" are
  both really "state survives an interruption").
- Several cases about the *same event*, one branch each (fires under condition A,
  doesn't fire under condition B, doesn't duplicate under condition C) — these read as
  one test with three assertions, not three tests.
- Structurally identical tests differing only in *which setting* changes (e.g. currency
  conversion and area-unit conversion follow the same "change a Settings value → verify
  displayed values update and match elsewhere" shape).

Always name the tradeoff when proposing a merge: losing isolated per-cause failure
signal in exchange for less execution time. That's a call for whoever runs the suite,
not something to apply unprompted.

**Do not touch — looks like the pattern above but isn't:**
- A genuine equivalence-partition boundary cluster (below-limit / at-limit / over-limit /
  re-entry-at-limit). These look similar to each other but each tests a distinct edge;
  merging them hides which specific boundary broke. This is exactly `L-002`'s
  "cover the boundary in three cases, not one" from the opposite direction — the rule
  that stops you from *writing* one case for three boundaries also stops you from
  *merging* three existing boundary cases back into one.

## Testability triage vs. wording fixes

Some findings in a review pass aren't fixable by editing case text at all — the blocker
is external to the suite. Recognise these and route them differently:

- **Needs a mechanism that doesn't exist yet or isn't documented** — e.g. every case in
  an A/B-gated feature assumes a way to force a test account into a specific experiment
  bucket, and no such mechanism is stated anywhere. This is the single most common
  systemic blocker: check for it **before** writing case text that assumes the answer.
- **Needs something only another role can provide** — a build from release engineering
  for an override-install test, a marketing-triggered push notification pointing at a
  specific listing, a second device/phone number for an incoming-call interrupt test,
  several pre-bucketed test accounts.
- **Needs inventory/data that may not exist in the test environment** — a specific
  listing type, a price at a specific digit count, enough distinct records to hit a
  stated numeric limit.

Don't rewrite fifteen individual cases to "fix" these — that doesn't fix anything, since
the blocker isn't in the wording. Collect them into one short pre-flight list ("confirm
these exist before this suite is run") and send it to whoever owns the dependency, in
parallel with the rest of the review, not as a blocker to finishing the review itself.

## Format discoveries from real exports

Confirmed from CSV re-exports pulled mid-cycle, not from documentation:

- **A `Configurations` column exists** in the Testmo export alongside Case ID / Case /
  Description / Expected, holding a platform tag (`iOS`, `Android`) for device-specific
  cases. Prefer this field for platform-scoping over embedding "iOS"/"Android" purely in
  prose, once it's confirmed available on the target project — it's structured data a
  tester's run view can filter on, prose can't.
- **Comparing two exports pulled at different points in the same review cycle is the
  reliable way to confirm what was actually applied**, versus what was *said* to be
  applied. A stated "done" and the actual exported state diverged more than once in this
  cycle — always re-pull and diff rather than trusting a verbal confirmation when the
  case content matters.
