---
name: inspect-live-screen
description: >
  Fast, read-only inspection of whatever screen is currently open on the connected
  device — resource-ids, locators, stability, and safety verdicts — without starting an
  Appium session or writing a test. Use when the user says "what's on screen", "find
  the locator for X", "what would the safety gate do with this", or before writing any
  new screen-object method that needs a real resource-id to target.
---

# Inspect Live Screen

Every screen-object method in this suite was written against a real dump, not a guess.
This is the loop that produces one, in under two seconds, with no Appium server and no
pytest run — `tools/adb.py`'s `page-source` command does a `uiautomator dump` directly
over adb, which is faster and has fewer moving parts than opening an Appium session just
to read `driver.page_source`.

## 1. Dump the current screen

Navigate the device to the screen by hand first — this tool reads whatever is already
on screen, it does not navigate.

```bash
python tools/adb.py page-source --output /tmp/screen.xml
```

If this fails, run through `session-preflight`'s device check (`adb devices -l`) before
assuming the tool is broken — a missing/unauthorized device is the far more common cause.

## 2. List elements, locators, and stability

```bash
python tools/pagesource.py parse --page-source /tmp/screen.xml
```

This is the same parser `crawler.py` and `crawl_safety.py` use — what it reports here is
exactly what the safety gate and any screen-object method will see. Look for:

- **A stable resource-id** — locator priority is `accessibility id` → `resource-id` →
  `uiautomator` → XPath last (CLAUDE.md). If the element you need has none of the first
  two, that's a real locator-quality gap, not something to work around with XPath by
  default — log it rather than silently reaching for the fragile option.
- **Rows with no resource-id of their own** — common in list rows where the id lives on
  a child `TextView` instead. `safe_tap_row_containing()` in
  [`tests/screen_objects/base.py`](../../../tests/screen_objects/base.py) is the pattern
  for that case: locate by `clickable(true)` + `childSelector(...)` (uiautomator, still
  above XPath), classify the labelled child since the row itself carries no identity.
- **A resource-id shared across multiple elements** — plain `AppiumBy.ID` can't filter by
  text and will silently grab the first match. If several elements share an id, you need
  the `resource_id` + `text` combined locator `BaseScreen._by()` builds, not a bare id.

## 3. Check what the safety gate would do with it

Before wiring a tap into a screen object, know its verdict up front rather than
discovering it via a `SafetyRefusal` mid-test:

```bash
python tools/crawl_safety.py check --page-source /tmp/screen.xml
```

Shows every tappable element on the dump classified ALLOW / BLOCK / UNCERTAIN. For one
hypothetical element without a full dump (e.g. checking a resource-id you're about to
add before it exists on any captured screen):

```bash
python tools/crawl_safety.py explain --resource-id "favourite_cb" --text "Save" \
  --class android.widget.CheckBox
```

If the verdict surprises you — an element you expected BLOCK comes back ALLOW or
UNCERTAIN, or vice versa — stop here and use `diagnose-safety-refusal` rather than
guessing at a rule change.

## 4. Cross-check against captured context before treating anything as new

`context/element-inventory.json` and `context/screen-inventory.observed.md` may already
have this screen from a prior crawl. A fresh one-off dump is for the current moment
(build drift, a screen state the crawl never reached); it does not replace those files
and should not be hand-copied into them — `app-cartographer` is the only agent that
writes to `context/`.

## Done

You now have: the element's resource-id (or the honest absence of one), its locator
priority tier, and its safety verdict. That's everything `add-screen-test` needs to wire
a new screen-object method correctly on the first attempt.
