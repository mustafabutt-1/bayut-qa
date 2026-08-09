# Synthetic page-source fixtures

**These are not dumps of the real Bayut app.** They are hand-written UiAutomator XML,
built to exercise the tooling before a device is available. Nothing in them is evidence
about how Bayut is actually built.

In particular, `com.bayut.app` is a **placeholder package name**, not a verified one.
Get the real value from `adb shell pm list packages | grep -i bayut` and put it in
`.env` as `BAYUT_APP_PACKAGE`.

## What each fixture is for

| File | Exercises |
|---|---|
| `01-search-results.xml` | Listing cards with and without stable identifiers, filter chips, tab bar, a card with **no** resource-id or content-desc (must come back UNCERTAIN, and appear in the testID ask) |
| `02-listing-detail.xml` | The dangerous surface: Call / WhatsApp / Email contact bar, Share, Report. All must be BLOCKED. Also carries "Reference no. 7419283" as plain unidentified text, to prove the listing-ID scan reads non-clickable views |
| `03-listing-detail-ar.xml` | The same screen in Arabic, with contact buttons that have **no** resource-id and **no** content-desc — only Arabic text. Proves the blocklist catches lead controls in `ar-AE`, which is where a text-only blocklist would fail |

## Replace these

Once `app-cartographer` runs its first PASSIVE crawl, real dumps land in
`context/page_source/`. Keep these synthetic fixtures anyway: they are the regression
tests for `crawl_safety.py`, and they must keep passing when the real ones change.

## Verify the tooling against them

```bash
python tools/crawl_safety.py selftest
python tools/crawl_safety.py --app-package com.bayut.app check \
    --page-source tests/fixtures/page_source/02-listing-detail.xml
python tools/crawler.py plan --page-source tests/fixtures/page_source/01-search-results.xml
python tools/crawler.py offline --fixtures-dir tests/fixtures/page_source --out /tmp/crawl-check
python tools/prober.py selftest
```
