# Device Matrix — Physical Android Devices

`run-orchestrator` reads this file to provision and shard. `failure-triage` reads it to
decide whether a failure is device-specific (→ likely REAL DEFECT, narrow scope) or
universal (→ likely REAL DEFECT, broad scope) or single-device-only (→ suspect
ENVIRONMENT).

**Status:** template. No real devices recorded. Serial numbers and any account details
belong in `.env`, never here — this file is checked in.

---

## Tiering rationale

We cannot test everything everywhere. Three tiers, chosen to catch the failure classes
that actually differ across Android devices:

- **T1 — Primary.** Every run, every suite. One modern mid-range device that matches the
  dominant real user profile.
- **T2 — Secondary.** Full regression only. One low-end/older-OS device (finds ANRs,
  memory, and layout truncation) and one large-screen/high-density device (finds layout
  and image defects).
- **T3 — Spot.** Manual or ad-hoc: foldables, tablets, very old OS, specific OEM skins.
  Not in the automated pool.

## Device table

| Slot | Tier | Model | OS / API | Screen / density | Serial | RAM | Role | Status |
|---|---|---|---|---|---|---|---|---|
| D1 | T1 | `TODO` | `TODO` | `TODO` | `$DEVICE_D1_SERIAL` | `TODO` | Primary EN runs | Not provisioned |
| D2 | T1 | `TODO` | `TODO` | `TODO` | `$DEVICE_D2_SERIAL` | `TODO` | Primary AR runs | Not provisioned |
| D3 | T2 | `TODO` low-end | `TODO` (oldest supported API) | `TODO` | `$DEVICE_D3_SERIAL` | `TODO` | Perf, ANR, truncation | Not provisioned |
| D4 | T2 | `TODO` large/high-density | `TODO` (newest API) | `TODO` | `$DEVICE_D4_SERIAL` | `TODO` | Layout, images, newest-OS behaviour | Not provisioned |

**Minimum viable pool is 2 devices** (one EN, one AR). Below that, parallel execution
buys nothing and the AR suite becomes serialised behind the EN suite.

## What must be recorded per device before it joins the pool

- [ ] `adb devices -l` output — serial, model, transport ID
- [ ] `adb shell getprop ro.build.version.release` and `ro.build.version.sdk`
- [ ] `adb shell wm size` and `wm density`
- [ ] OEM skin and version (MIUI / One UI / ColorOS …) — skins change permission dialogs,
      which breaks flows that a stock device passes
- [ ] Developer options: **stay awake on**, **animations off** (scale 0 for window,
      transition, animator — this alone removes a large share of Appium flake)
- [ ] Screen lock disabled, no PIN
- [ ] Google Play Services version — affects maps and social login
- [ ] Battery-optimisation exemption for the app under test, or background-kill during
      long runs will look like a defect
- [ ] Wi-Fi network + proxy reachability to the mitmproxy host

## Locale and configuration axes

| Axis | Values under test | Applied by |
|---|---|---|
| Locale | `en_AE`, `ar_AE` | `tools/adb.py set-locale` |
| Font scale | default, largest | `adb shell settings put system font_scale` |
| Display size | default, largest | `adb shell wm density` |
| Network | Wi-Fi, throttled, airplane | `tools/adb.py` + mitmproxy throttling |
| Dark mode | light, dark `[ASSUMED — verify]` app supports it | `adb shell cmd uimode night` |
| Permissions | granted, denied, "only this time" | `adb shell pm grant/revoke` |

Not every axis crosses with every other — feed the axes into `tools/pairwise.py` with the
functional parameters rather than running the full cross product.

## Sharding policy

- Shard by **test file**, not by test, so screen-object state and app reset stay coherent.
- `arabic`-marked tests pin to the AR device; they must not be scheduled on an EN device
  with a mid-run locale switch — locale switching mid-session restarts the app and is a
  documented flake source.
- `flaky`-marked tests run **last**, serially, on the primary device, and their results
  never gate a release call.
- Max parallelism = number of physical devices. Do not oversubscribe a device with
  multiple Appium sessions; UiAutomator2 does not tolerate it.

## Known unknowns

- `UNKNOWN — needs manual verification`: Bayut's minimum supported Android API level.
  Determines the T2 low-end device.
- `UNKNOWN — needs manual verification`: real user OS/device distribution for Bayut UAE.
  Ask analytics — picking devices without it is guesswork. Listed in `docs/ASKS.md`.
- `UNKNOWN — needs manual verification`: whether devices will live on a desk or in a
  rack, and whether they will be reachable when the office network changes. Device farm
  reliability is a top operational risk (`docs/RISKS.md`).
