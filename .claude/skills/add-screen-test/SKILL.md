---
name: add-screen-test
description: >
  Add a new test for a screen or control — locate real resource-ids, write the screen-
  object method with correct locator priority, wire the safety classification, and place
  the test in the right checklist-numbered suite folder (consequential or not). Use when
  the user says "add a test for X", "write a screen object for Y", or asks to cover a
  regression-checklist item that has no test yet.
---

# Add Screen Test

Every test in `tests/suites/` follows the same shape: a Page Object method in
`tests/screen_objects/`, called from a checklist-numbered test module, going through
`safe_tap()` (or the deliberate, gated exception) — never a bare `.click()`. This skill
is that shape, in order.

## 0. Ground it in a real dump first

Don't write a locator from memory or from `context/`'s hypothesis files. Run
`inspect-live-screen` against the actual screen — resource-id, locator tier, and safety
verdict all come from there, not from guessing.

## 1. Decide: does this action create data on production?

This is the fork that decides everything downstream. Check
[`docs/GUARDRAILS.md`](../../../docs/GUARDRAILS.md) and the `PROD-BLOCK-*` rules in
`tools/crawl_safety.py` (`python tools/crawl_safety.py rules`). If the control you're
testing is one of the 11 production-block categories (favourites, saved searches,
sign-up, TruEstimate, Portfolio, claims, seller leads, BayutGPT, profile edits, sharing,
lead-contact outside the sanctioned agency):

- **Read-only assertion (control exists, gate refuses it):** normal test, normal folder.
  Use `assert_blocked(resource_id=..., accessibility_id=..., text=...)` — never taps,
  asserts the verdict is `BLOCK`. This is what most checklist items actually need: proof
  the control is there and the guard genuinely refuses it, not proof the mutation works.
- **The mutation itself must be verified for real** (e.g. "does a favourite actually
  persist"): it goes in a `consequential/` subfolder, uses `deliberate_tap()` /
  `deliberate_tap_at()` from `tests/screen_objects/consequential.py`, and is gated behind
  `RUN_CONSEQUENTIAL_TESTS=1`. Nothing outside `consequential/` may import that module —
  it's a layout boundary, not just a convention. See `test_favourites.py` in both
  `tests/suites/20_favourites/` (presence+blocked) and
  `tests/suites/20_favourites/consequential/` (the real favourite-and-verify) for the
  paired pattern.
- **Lead-contact controls** (Call/WhatsApp/Email/Report agent) stay BLOCK always, on
  every screen except the sanctioned test agency (Explorer Real Estate, Al Napoca) — and
  even there only through `policy.lead_test(elements)` / `_assert_lead_allowed()`, which
  re-reads the agency off the live screen rather than trusting the caller. Never write a
  test that taps a lead control outside that one exemption.

If you're not sure which bucket a control falls in, that uncertainty is the answer:
default to read-only assertion, and raise it rather than deciding alone — a wrong guess
here is exactly the "hundred spurious leads" failure mode CLAUDE.md warns about.

## 2. Write the screen-object method

Add to the relevant file in `tests/screen_objects/` (one class per screen — check if one
already exists before creating a new file). Rules from `base.py`'s own docstring, all
non-negotiable:

- **Locator priority**: `accessibility id` → `resource-id` → `uiautomator` → XPath last.
  `BaseScreen._by()` already builds the common shapes, including the `resource_id` +
  `text` combined uiautomator locator for elements sharing an id. Log a warning on any
  XPath use — CLAUDE.md requires it, so fragility stays visible rather than silent.
- **No `.click()` outside `safe_tap()`** (or the isolated `consequential.py` exception).
  There is exactly one tap path in this suite for a reason — see `SafetyRefusal`'s own
  docstring in `base.py`.
- **Explicit waits only.** `wait_for()` / `WebDriverWait`, never `time.sleep()`.
- **Read-only helpers stay read-only.** If a method only needs to locate and report
  (e.g. `locate_favourite_checkbox()`), don't give it a tap it doesn't need — that's what
  kept the non-consequential favourites test from ever risking a real mutation.

## 3. Place the test in the right suite folder

Folders are numbered to match `docs/REGRESSION-CHECKLIST.md`'s own sections — match the
existing number, don't invent a new one unless the checklist genuinely has no section for
this control yet (check `context/checklist-corrections.md` first; it lists 13 unmapped
feature areas that may already cover it). Consequential tests live in a `consequential/`
subpackage under the same number, each needing its own `__init__.py` — `pytest.ini`'s
`--import-mode=importlib` exists specifically because several checklist folders each have
their own same-named `consequential` subpackage that would otherwise collide (D-029).

## 4. Verify before calling it done

```bash
python tools/crawl_safety.py selftest    # must still pass clean — you may have touched rules
```

Then run the specific test live (see `COMMANDS.md` for the exact PowerShell/bash
invocation, including `RUN_CONSEQUENTIAL_TESTS=1` if applicable) — not the whole suite,
just the one you added, and read the actual failure output if it doesn't pass first try.
A `SafetyRefusal` here isn't a bug to route around; see `diagnose-safety-refusal`.

## 5. Record anything non-obvious

If the fix or the locator involved a real gotcha (a shared resource-id, a row with no id
of its own, a rule that needed extending), add an entry to `docs/DECISIONS.md` — that's
what let this exact skill get written instead of re-discovering the same bugs cold every
session.
