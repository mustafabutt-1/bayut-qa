---
name: diagnose-safety-refusal
description: >
  Diagnose a SafetyRefusal, an unexpected UNCERTAIN/BLOCK/ALLOW verdict, or "why won't
  this tap" — and fix it at the correct layer instead of loosening a match carelessly.
  Use when a test raises SafetyRefusal, when crawl_safety.py's check/explain output
  doesn't match expectation, or when the user asks why the safety gate did something.
---

# Diagnose Safety Refusal

A `SafetyRefusal` or a surprising verdict is a signal, not a bug in the test — CLAUDE.md
and `SafetyRefusal`'s own docstring in `base.py` are explicit that it means one of two
things: the test is exercising a flow that's supposed to stay manual-only, or a real
behavioural change moved a consequential control somewhere the allowlist doesn't cover
yet. **Never silence it by widening a rule from inside a test.** Work out which of the
two it is before touching anything.

## 1. Reproduce the verdict directly, outside the test

Don't debug this by re-running pytest repeatedly. Get the exact element and ask the gate
directly:

```bash
# against a real dump — see inspect-live-screen for how to get one
python tools/crawl_safety.py check --page-source /tmp/screen.xml

# against one hypothetical element, no dump needed
python tools/crawl_safety.py explain --resource-id "..." --text "..." \
  --content-desc "..." --class android.widget.CheckBox
```

`explain` prints which rule matched (if any) and why. That is almost always faster than
reasoning about the regex from reading `crawl_safety.py` cold.

## 2. Know the three failure shapes

**A. Genuinely BLOCK, correctly.** The test is targeting a real consequential control
(sign-up, favourite, lead-contact, saved search, ...). This is not a diagnosis task —
it's a design question: does this test belong in a `consequential/` folder using
`deliberate_tap()`, or should it be `assert_blocked()` instead? See `add-screen-test`
step 1.

**B. False ALLOW / UNCERTAIN — a block rule should have caught this and didn't.** The
most dangerous shape, because a missed block risks a real tap on a live production
action. Check, in order:

1. Does a `PROD-BLOCK-*` or `BLOCK-*` rule exist for this category at all?
   `python tools/crawl_safety.py rules`
2. If a rule exists, does its pattern actually cover this element's exact resource-id /
   text / content-desc? **Word-normalisation is the single most common cause of a miss
   here.** `_match_candidates()` in `crawl_safety.py` turns `_`/`-`/`.`/`:`/`/` into
   spaces before matching, so `\bcall\b` matches `call_agent_button` — but a pattern
   written as `favou?rite\b` will *not* match `favourite_cb`, because normalisation turns
   `favourite_cb` into `favourite cb`, and the boundary the raw underscored id never had
   suddenly exists in the normalised form and splits the word. This exact bug shipped
   once: `favourite_cb` fell through `PROD-BLOCK-FAVOURITE` to `ALLOW-NAV-TABS`'s generic
   "favourites" word list. See `docs/DECISIONS.md` D-041 for the full trace and fix.
3. Does an `ALLOW-*` rule match first when it shouldn't? Block always beats allow in
   `evaluate()` — if a genuinely dangerous element is coming back ALLOW, the bug is that
   no block rule matched at all (step 1/2), not that allow "won."

**C. False BLOCK / UNCERTAIN — a control that should work is refused.** Check whether the
*classified* element is actually the one being tapped. `safe_tap()` classifies the target
by re-parsing `page_source` fresh and matching on the same locator the test used — if a
row has no resource-id of its own and the label child is what should be classified (the
`safe_tap_row_containing()` pattern in `base.py`), classifying the anonymous row itself
will always come back UNCERTAIN by design, and that's a locator problem, not a rules
problem. Also check for a shared resource-id across multiple elements — a bare
`AppiumBy.ID` locator can silently match a *different* element than the one on screen,
which then gets classified and refused for a completely unrelated reason.

## 3. Fix at the correct layer

| Root cause | Fix |
|---|---|
| Missing block rule for a real data-creation/lead action | Add/extend a `BLOCK-*` or `PROD-BLOCK-*` pattern in `crawl_safety.py`, verify both directions (the bad case now blocks, legitimate neighbors still allow) |
| Word-normalisation gap (case B.2) | Extend the specific rule's regex to cover the underscored/dashed form; don't loosen the generic allow rule instead |
| Wrong element being classified (case C) | Fix the screen-object locator/classification target, not the safety rule — the rule may be correctly refusing the wrong thing you pointed it at |
| Genuinely consequential, correctly refused | Not a fix at all — go to `add-screen-test` step 1 and decide `assert_blocked()` vs `consequential/` |

## 4. Verify the fix didn't break anything else

```bash
python tools/crawl_safety.py selftest
```

Must stay at N/N — check the current count against `docs/PROJECT-STATE.md` before and
after; a rule change that fixes one case while silently dropping another's coverage is
worse than the original bug. Then re-run `explain`/`check` for both the case you fixed
*and* a couple of neighboring legitimate cases (e.g. the nav-tab "Favourites" label
itself, if you touched a favourite-related pattern) to confirm you widened nothing you
didn't mean to.

## 5. Log it

A rule gap is exactly the kind of non-obvious design decision `docs/DECISIONS.md` exists
for — root cause, the fix, and what it would have cost if missed (D-041 is the template).
