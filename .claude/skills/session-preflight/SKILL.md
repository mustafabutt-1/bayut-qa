---
name: session-preflight
description: >
  Run at the start of any session that will touch the live device or run tests —
  starts Appium correctly, confirms the safety gate, and checks for build drift before
  anything else happens. Use when the user says "start a session", "let's test", "run
  the suite", or before any live crawl/probe/pytest run when Appium/device state is
  unknown. Skips steps that are already satisfied.
---

# Session Preflight

Every live-device mistake this project has actually hit traces back to skipping one of
these checks. Run them in order; stop at the first failure rather than pushing through.

## 1. Device

```bash
adb devices -l
```

Exactly one `device` (not `unauthorized`, not `offline`). `DEVICE_D1_SERIAL` in `.env`
is **optional** — `tests/conftest.py` auto-picks the single connected device via
`tools/adb.py`'s `Adb.require_device()`. Only set it to disambiguate multiple devices.
If it's set and pointing at a now-disconnected device, blank it rather than updating it —
that's a stale value, not a config to maintain.

## 2. Appium server

**Never use bash-style `&` backgrounding if the shell is PowerShell** — it's a hard
parse error there (`The ampersand (&) character is not allowed`). Use the Bash tool's
`run_in_background: true`, or `Start-Process` if genuinely in PowerShell:

```bash
appium --port 4723 --allow-insecure=uiautomator2:adb_shell
```

The `--allow-insecure=uiautomator2:adb_shell` flag is required — `FindMyAgentHubScreen.search()`
uses `mobile: shell` for text entry (send_keys() doesn't trigger that field's live
search listener). Appium 3.x requires the `<driverName>:<featureName>` form; the bare
`adb_shell` flag crashes server startup outright, it doesn't just refuse the feature.

Confirm it's actually up before moving on — a `curl`/`Invoke-RestMethod` run
immediately after backgrounding the server can hit it before it's finished loading the
driver (8–9s is typical), which reads as "server down" when it's just still starting:

```bash
curl -s http://127.0.0.1:4723/status
```

## 3. Safety gate — non-negotiable, every session

```bash
python tools/crawl_safety.py selftest
```

Must read **N/N assertions passed** with no failures. Do not proceed to any live crawl,
probe, or consequential test if this doesn't pass cleanly. The exact N drifts as rules
get added — check the printed number against what's currently in
`docs/GUARDRAILS.md`/`COMMANDS.md`; if they disagree, trust the live run and update the
docs, not the other way around.

## 4. Build match

The device's installed app build must match what `context/` was captured against, or
every locator failure that follows will look like a real bug when it's actually build
drift:

```bash
adb -s <serial> shell dumpsys package com.bayut.bayutapp | grep versionName
grep BAYUT_BUILD_VERSION .env
```

`tests/conftest.py`'s `driver` fixture already checks this automatically and prints a
loud `*** BUILD MISMATCH ***` warning at the top of any pytest run if they disagree
(docs/DECISIONS.md D-030) — this manual check is for live crawl/probe work outside
pytest, which doesn't get that fixture's protection.

If they genuinely differ (a new build was installed on purpose), decide explicitly
whether to re-crawl (`context/` regenerates) or note the drift and continue — don't
silently proceed on stale context.

## Done

At this point: one device connected, Appium up with the right flags, safety gate
verified clean, build confirmed current. Proceed to whatever the actual task is —
`COMMANDS.md` has the full command reference for running tests, crawling, and probing.
