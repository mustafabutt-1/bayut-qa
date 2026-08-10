# Setup — from a fresh machine to a first crawl

Everything here has been verified on Windows 11 + Python 3.13 + Appium 3.5.2. macOS and
Linux notes are included where the commands differ.

**Nothing in this repo hardcodes a machine-specific value.** Paths, serials, hosts and
package names all live in `.env`. If you find one inline in a `.py` file, that is a bug.

---

## 0. Time budget

| Step | Time | Needs hardware |
|---|---|---|
| 1–4 Software install | 30–45 min | no |
| 5 Verify without a device | 2 min | no |
| 6 Device preparation | 20 min | yes |
| 7 mitmproxy + certificate | 20–40 min | yes |
| 8 First crawl | 30–60 min | yes |

You can complete steps 1–5 and confirm the whole toolchain works before any device
exists. Do that first — it separates "my setup is wrong" from "the app behaved oddly".

---

## 1. Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ (24 verified) | `node --version` |
| Java JDK | 11+ | `java -version` — required by the uiautomator2 driver |
| Android SDK platform-tools | any recent | `adb version` |
| Git | any | `git --version` |

### Android platform-tools

Either install Android Studio (bundles it), or download platform-tools standalone from
`developer.android.com/studio/releases/platform-tools` and put it on `PATH`.

Typical locations:

- Windows: `%LOCALAPPDATA%\Android\Sdk\platform-tools`
- macOS: `~/Library/Android/sdk/platform-tools`
- Linux: `~/Android/Sdk/platform-tools`

If `adb` is not on `PATH`, set `ADB_PATH` in `.env` to the full binary path. Every tool
reads it.

---

## 2. Appium server and driver

```bash
npm install -g appium
appium driver install uiautomator2
```

Verify:

```bash
appium --version                  # expect 3.x
appium driver list --installed    # expect uiautomator2@8.x
```

**Version pairing matters.** Appium server 3.x needs Appium-Python-Client **6.x**. The
4.x client line targets server 2.x and will fail at the first `webdriver.Remote` call
with a confusing error. `requirements.txt` pins 6.0.0 for this reason.

Optional health check — start the server and probe it:

```bash
appium --port 4723 &
curl -s http://127.0.0.1:4723/status
# {"value":{"ready":true,...,"build":{"version":"3.5.2"}}}
```

Base path is `/`, which matches the `APPIUM_SERVER_URL` default in `.env.example`.

**Always start the server with `--allow-insecure=uiautomator2:adb_shell`.** One screen
(`FindMyAgentHubScreen.search()`) types via Appium's `mobile: shell` extension instead of
`send_keys()`, because `send_keys()` never triggers that field's live search-as-you-type
listener (docs/DECISIONS.md D-019/D-026). Without this flag, `mobile: shell` calls fail
outright. Appium 3.x requires the `<driverName>:<featureName>` form — the bare
`adb_shell` flag crashes server startup instead of just refusing the feature:

```bash
appium --port 4723 --allow-insecure=uiautomator2:adb_shell &
```

---

## 3. Python environment

```bash
cd bayut-qa
python -m venv .venv

# Windows (Git Bash)
.venv/Scripts/python.exe -m pip install -r requirements.txt
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
# macOS / Linux
source .venv/bin/activate && pip install -r requirements.txt
```

`.venv/` is gitignored. Never commit it.

---

## 4. Configuration

```bash
cp .env.example .env
```

Fill in what you know now; the rest arrives once a device is attached. `.env` is
gitignored and **must never be committed** — it holds tokens and account credentials.

| Variable | Where it comes from |
|---|---|
| `BAYUT_APP_PACKAGE` | `adb shell pm list packages \| grep -i bayut` (needs a device) |
| `BAYUT_APP_ACTIVITY` | `adb shell dumpsys window \| grep mCurrentFocus` with the app open |
| `ADB_PATH` | only if `adb` is not on `PATH` |
| `DEVICE_D1_SERIAL` … | `adb devices -l` |
| `MITM_HOST` / `MITM_PORT` | the machine running mitmproxy, reachable from the device |
| `TESTMO_*` | Testmo instance URL + personal API token |
| `CLICKUP_*` | read-scoped token if your plan supports it |
| `TEST_USER_*` | a dedicated QA account with a phone number you control |

**`com.bayut.app` appears in fixtures and examples throughout this repo. It is a
placeholder, not a verified package name.** Replace it everywhere once you have the real
one.

---

## 5. Verify the toolchain — no device needed

This is the gate. Run all four; all four must pass.

```bash
python tools/crawl_safety.py selftest
#   expect: 65/65 assertions passed
#           "Blocklist and allowlist behave as specified. Safe to crawl."

python tools/prober.py selftest
#   expect: 28/28 assertions passed

python tools/crawler.py offline \
    --fixtures-dir tests/fixtures/page_source --out /tmp/crawl-check
#   expect: screens 3, blocked 10, uncertain 3, and 7 report files written

python tools/crawl_safety.py --app-package com.bayut.app check \
    --page-source tests/fixtures/page_source/02-listing-detail.xml
#   expect: Call, WhatsApp, Email, Share, Report all BLOCK
```

**If the last one does not show all five as BLOCK, stop. Do not crawl.** The guard is
the only thing preventing real leads being sent to real agencies.

Also useful with no device — inspect every adb command without running it:

```bash
python tools/adb.py --dry-run reset-app --package com.bayut.app --launch
python tools/adb.py --dry-run deeplink --url "bayut://search?purpose=rent"
```

---

## 6. Device preparation

Connect an Android device by USB, enable Developer Options and USB debugging, and accept
the RSA prompt on the device screen.

```bash
adb devices -l                # must show "device", not "unauthorized" or "offline"
python tools/adb.py devices   # adds OS, SDK, size, density, locale
python tools/adb.py prepare   # animations off, stay awake, long screen timeout
```

`prepare` applies the settings that remove a large share of Appium flake. It cannot do
everything — finish these by hand:

- [ ] Screen lock / PIN **disabled**
- [ ] App under test **exempt from battery optimisation** (otherwise long runs get
      background-killed and it looks like a defect)
- [ ] Device on the same network as the mitmproxy host
- [ ] Record the OEM skin (MIUI / One UI / ColorOS) in `context/device-matrix.md` —
      skins change permission dialogs, which breaks flows a stock device passes

Then capture the two values you still need:

```bash
adb shell pm list packages | grep -i bayut
python tools/adb.py info --package <real.package.name>   # writes a JSON snapshot
```

Put both in `.env`.

### Locale switching — read before planning the Arabic suite

**There is no reliable pure-adb locale switch on a non-rooted modern Android device.**
`tools/adb.py` deliberately refuses `settings put system system_locales`, because that
command appears to succeed and frequently does nothing until reboot — which would
silently produce an English crawl labelled Arabic. Wrong data labelled correct is worse
than no data.

Three real options:

| Method | Works | Cost |
|---|---|---|
| `--method root` | rooted device only | needs a rooted test device |
| `--method helper` | unrooted | install the ADB Change Language helper APK first |
| in-app language setting | always | a UI action, so `crawler.py` performs it, not adb. Most faithful to a real user. |

Always verify afterwards — never assume:

```bash
python tools/adb.py get-locale
```

---

## 7. mitmproxy and the certificate

Needed for the API oracle and for the pinning check. Install it (`pip install mitmproxy`
is already in `requirements.txt`), then:

```bash
mitmdump -w runs/crawl-01/capture.flow
python tools/adb.py proxy set --host $MITM_HOST --port 8080
```

On the device, open `http://mitm.it` and install the CA certificate. On Android 7+ a
user-installed CA is **not** trusted by apps by default unless the app opts in via its
network security config.

**This is the moment certificate pinning shows up.** If the app makes no requests through
the proxy, `oracle.py` and `har_diff.py` cannot be built until dev ships a debug build
whose network security config trusts user CAs. The crawler's watchdog reports this within
5 minutes rather than at the end — see `docs/ARCHITECTURE.md` §7.

To remove the proxy afterwards:

```bash
python tools/adb.py proxy clear
```

---

## 8. First crawl

```bash
appium --port 4723 --allow-insecure=uiautomator2:adb_shell &
mitmdump -w runs/crawl-01/capture.flow &

python tools/crawl_safety.py selftest        # 67/67 or stop

python tools/crawler.py crawl \
    --package $BAYUT_APP_PACKAGE \
    --locale en-AE \
    --mitm-flow-file runs/crawl-01/capture.flow \
    --out context \
    --artifacts runs/crawl-01
```

**Watch the first five minutes** for the pinning verdict. Then read, in this order:

1. `context/pinning-check.md`
2. `context/listing-id-visibility.md`
3. `context/crawl-uncertain.md`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `adb not found` | not on PATH | set `ADB_PATH` in `.env` |
| device `unauthorized` | RSA prompt not accepted | unlock the device, accept "Allow USB debugging" |
| device `offline` | stale adb daemon | `adb kill-server && adb start-server` |
| `2 devices connected; pass --serial` | more than one attached | `--serial <serial>` or set `ANDROID_SERIAL` |
| Appium `Could not find a driver` | driver not installed | `appium driver install uiautomator2` |
| `webdriver.Remote` fails immediately | client/server version mismatch | client 6.x with server 3.x — check `pip show Appium-Python-Client` |
| Crawl reaches only 2–3 screens | strict mode, most elements UNCERTAIN | expected on run one. Review `crawl-uncertain.md`, build `crawl-allowlist.yaml`, re-crawl |
| Zero proxy traffic | certificate pinning, or proxy unreachable | see `context/pinning-check.md` for the two-step confirmation |
| Arabic tests behave like English | locale did not actually switch | `adb.py get-locale`; see §6 |
| Everything fails on one device only | app failed to install, or stale build | `adb shell dumpsys package <pkg> \| grep versionName` |

---

## What "set up correctly" means

You are ready when all of these are true:

- [ ] `crawl_safety.py selftest` → 65/65
- [ ] `prober.py selftest` → 28/28
- [ ] `crawler.py offline` → 7 reports written
- [ ] The dangerous fixture shows Call / WhatsApp / Email / Share / Report all **BLOCK**
- [ ] `adb devices` shows exactly one device in state `device`
- [ ] `appium --version` is 3.x and `uiautomator2` is installed
- [ ] `.env` has a real `BAYUT_APP_PACKAGE` — not the placeholder
- [ ] `docs/PROJECT-STATE.md` §5 decisions are answered, or you know which are still open
