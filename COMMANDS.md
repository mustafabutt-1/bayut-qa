# Commands — Bayut QA Suite

Copy-paste reference for running this suite by hand. Every command here has been run
live against the real app; nothing is aspirational. If a command's output stops
matching what's documented, the doc is wrong — fix the doc, don't trust it over the
terminal.

Run everything from the repo root (`Bayut/`), with a device connected and Appium
running (see `docs/SETUP.md` if either isn't set up yet).

---

## 0. Before every session

All commands below are shown for **PowerShell** (this project's primary shell on
Windows) — the two commands that start a background server differ from bash. A `bash`
variant follows each one where it differs.

```powershell
# One device connected — DEVICE_D1_SERIAL in .env is optional now (auto-detected).
# Only set it if more than one device is attached at once.
adb devices -l

# Appium server, with the flag the search-typing workaround needs (D-026).
# PowerShell has no bash-style trailing `&` for backgrounding — use Start-Process,
# or open a second terminal tab/window and just run the command directly in it.
Start-Process appium -ArgumentList "--port 4723 --allow-insecure=uiautomator2:adb_shell"
Start-Sleep -Seconds 5
Invoke-RestMethod http://127.0.0.1:4723/status
```

```bash
# bash equivalent
appium --port 4723 --allow-insecure=uiautomator2:adb_shell &
curl -s http://127.0.0.1:4723/status
```

```powershell
# The safety gate. Run this before every session — not optional.
python tools/crawl_safety.py selftest
#   expect: 125/125 assertions passed
#           default environment : production
#           lead allowlist      : ['Explorer Real Estate']
# If this doesn't say 125/125, STOP — do not run anything else until it does.
```

`.env` must exist (copy from `.env.example`) with at minimum `BAYUT_APP_PACKAGE` set.
See `docs/SETUP.md` for the full walkthrough on a fresh machine.

---

## 1. Run the whole default suite

The default suite is everything **except** `consequential/` tests — no real logout,
no real lead. Safe to run any time, any number of times.

```bash
python -m pytest tests/suites/ -v
```

Add `--tb=short` for terser failure output on a big run, or `-x` to stop at the first
failure while debugging.

---

## 2. Run one module (by regression-checklist section)

Every folder under `tests/suites/` is named after a `docs/REGRESSION-CHECKLIST.md`
section number, or lives under `feature_areas/` for the checklist's unnumbered feature
sections. Run just one:

```bash
python -m pytest tests/suites/00_smoke/ -v                              # smoke
python -m pytest tests/suites/03_app_override/ -v                       # §3  App override / data retention
python -m pytest tests/suites/04_sign_in_up/ -v                         # §4  Sign in / Sign up (default part only)
python -m pytest tests/suites/05_leads/ -v                              # §5  Leads (default part only)
python -m pytest tests/suites/10_home_screen/ -v                        # §10 Home screen
python -m pytest tests/suites/11_filters_search/ -v                     # §11 Filters & search
python -m pytest tests/suites/13_location_screen/ -v                    # §13 Location screen
python -m pytest tests/suites/15_listing_fat_cards/ -v                  # §15 Listing fat cards
python -m pytest tests/suites/16_lpv_inline_widgets/ -v                 # §16 LPV inline widgets/filters
python -m pytest tests/suites/18_detail_page_dpv/ -v                    # §18 Detail page (DPV)
python -m pytest tests/suites/20_favourites/ -v                         # §20 Favourites
python -m pytest tests/suites/21_more_screen/ -v                        # §21 More screen
python -m pytest tests/suites/feature_areas/activity_log/ -v            # Feature area: Activity Log
python -m pytest tests/suites/feature_areas/trubroker_find_my_agent/ -v # Feature area: TruBroker & Find My Agent
```

Run a single test file, or a single test, the normal pytest way:

```bash
python -m pytest tests/suites/11_filters_search/test_filters_search.py -v
python -m pytest tests/suites/11_filters_search/test_filters_search.py::test_buy_rent_picker -v
```

Filter by name across the whole suite with `-k`:

```bash
python -m pytest tests/suites/ -k "favourite" -v
```

### Checklist sections with no folder — not automated, on purpose

`§1, 2, 6, 7, 8, 9, 12, 14, 17, 19, 22, 23, 24, 25, 26` and feature areas `Dubai
Transactions, BayutGPT, TruEstimate, TruBroker Stories, Off-Plan Projects, Notification
Center, Firebase Crashlytics` have no test folder. Each is blocked for a specific,
documented reason — a real environment/hardware dependency (`§26` device-specific,
`§1` fresh install), a `PROD-BLOCK-*` guardrail (`§19` Saved Searches, BayutGPT,
TruEstimate), or a destructive action never worth automating on production (`§22`
Delete account). See `docs/GUARDRAILS.md` for the production blocklist and
`docs/PROJECT-STATE.md` for the full open-items list. This isn't a gap to quietly fill
— it's the honest boundary of what read-path automation on production can cover.

---

## 3. Consequential tests — real actions, opt-in only

These sign a real account out and back in, submit a real lead, or favourite a real
listing. Gated behind an environment variable that a bare `pytest tests/` can never set
by accident. PowerShell has no bash-style `VAR=value command` inline prefix — set it as
its own statement first (it stays set for the rest of that terminal session):

```powershell
$env:RUN_CONSEQUENTIAL_TESTS = "1"
python -m pytest tests/suites/04_sign_in_up/consequential/ -v
python -m pytest tests/suites/05_leads/consequential/ -v
python -m pytest tests/suites/20_favourites/consequential/ -v
python -m pytest tests/suites/03_app_override/consequential/ -v
```

```bash
# bash equivalent
RUN_CONSEQUENTIAL_TESTS=1 python -m pytest tests/suites/04_sign_in_up/consequential/ -v
RUN_CONSEQUENTIAL_TESTS=1 python -m pytest tests/suites/05_leads/consequential/ -v
RUN_CONSEQUENTIAL_TESTS=1 python -m pytest tests/suites/20_favourites/consequential/ -v
RUN_CONSEQUENTIAL_TESTS=1 python -m pytest tests/suites/03_app_override/consequential/ -v
```

Without `RUN_CONSEQUENTIAL_TESTS=1` these show as `SKIPPED`, not silently absent —
confirm that's what you see before assuming the suite is "all green".

The lead test only ever targets **Explorer Real Estate** (the QA team's own sanctioned
test agency) — `tools/crawl_safety.py`'s lead gate (`docs/GUARDRAILS.md` rule 3) reads
the live screen itself and refuses to allow a lead CTA against any other agency, even
if a test tried to point it elsewhere.

---

## 4. Everything together

```powershell
$env:RUN_CONSEQUENTIAL_TESTS = "1"
python -m pytest tests/suites/ -v
```

Only do this deliberately — it will really log the test account out/in, really submit a
lead to Explorer Real Estate, and really favourite a real listing.

To go back to the safe default for the rest of the session:

```powershell
Remove-Item Env:\RUN_CONSEQUENTIAL_TESTS
```

---

## 5. Safety-gate tools (no device needed)

```powershell
python tools/crawl_safety.py selftest                     # 125/125, run before every session
python tools/crawl_safety.py rules                         # print every active rule
python tools/crawl_safety.py explain --resource-id "..." --text "..."   # one hypothetical element
python tools/crawl_safety.py --environment staging selftest  # compare staging behaviour

python tools/crawl_safety.py --app-package com.bayut.bayutapp check `
    --page-source context/page_source/<file>.xml            # classify a real captured screen
```

`--app-package` (and `--environment`, `--config`) are **global** options — they go
before the subcommand (`check`/`selftest`/`rules`/`explain`), not after. Putting them
after, like `check --app-package ...`, fails with `unrecognized arguments`.

PowerShell line-continuation is a backtick (`` ` ``) at end-of-line, not bash's `\` — used
above.

---

## 6. Crawling — refreshing `context/`

**Live crawl** (drives the real device, safety-gated, several minutes):

```powershell
python tools/crawler.py crawl `
    --package com.bayut.bayutapp `
    --locale en-AE `
    --out context `
    --artifacts runs/crawl-NN `
    --preserve-app-state `
    --bootstrap-content-desc Home `
    --max-actions 400
```

Only re-crawl when the **app build** changes (`BAYUT_BUILD_VERSION` in `.env` vs. what's
actually installed — the `driver` fixture warns loudly on a mismatch, D-030). Switching
physical devices alone never requires a re-crawl.

**Offline rebuild** — reprocesses every `context/page_source/*.xml` capture already on
disk into a fresh `screen-inventory.observed.md` / `element-inventory.json` /
`crawl-blocked.md` / `crawl-uncertain.md`, with **no device or live crawl needed**:

```powershell
python tools/crawler.py offline `
    --fixtures-dir context/page_source `
    --out context `
    --locale en-GB `
    --package com.bayut.bayutapp
```

Do this whenever `context/`'s summary files feel stale but you haven't captured
anything new — it's free, local, and safe to re-run any time.

`context/screen-flows.observed.md` is hand-maintained from the screen objects'
own navigation methods (`tests/screen_objects/*.py`), not generated by either crawl
command — update it in the same commit if a screen object's navigation changes.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'consequential...'` | `pytest.ini`'s `--import-mode=importlib` isn't being picked up | run pytest from the repo root, where `pytest.ini` lives |
| Wall of `element not found` failures out of nowhere | Connected device is running a different app build than `.env` expects | check the `*** BUILD MISMATCH ***` warning printed at the top of the run (D-030) |
| `RuntimeError: ... not among connected devices` | Stale `DEVICE_D1_SERIAL` in `.env` pointing at a disconnected device | blank it out — auto-detection only needs it when 2+ devices are attached |
| `SafetyRefusal: refusing to tap ...` | Working as intended | either the control genuinely should stay manual, or it's a new, never-classified element — add a scoped rule to `context/crawl-allowlist.yaml`, don't loosen the shared defaults |
| `2 devices connected; pass --serial` (from `tools/adb.py`/`crawler.py` directly, not pytest) | Two devices attached, tool can't guess which | pass `--serial <serial>` explicitly |
