# Bayut QA — Agentic Test System

Black-box QA automation for the **Bayut UAE Android app**, built and owned by the manual
QA team at Dubizzle Labs.

The dev team ships with agents. QA is now the bottleneck, and the only independent check
on AI-written code. This system is how QA keeps up without becoming a rubber stamp — and
its independence from the dev codebase is the point, not a limitation.

---

## Start here

| I want to… | Read |
|---|---|
| **know where the project actually is** | **[docs/PROJECT-STATE.md](docs/PROJECT-STATE.md)** |
| **start a Claude Code session on this repo** | **[docs/PROMPTS.md](docs/PROMPTS.md)** — paste prompt **P1** |
| get it running on my machine | [docs/SETUP.md](docs/SETUP.md) |
| understand how and why it works | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| know why something was decided | [docs/DECISIONS.md](docs/DECISIONS.md) |
| see which agents exist | [.claude/agents/README.md](.claude/agents/README.md) |
| write or review a manual Testmo suite | [docs/TESTMO-SUITE-DESIGNER.md](docs/TESTMO-SUITE-DESIGNER.md) |

If you are Claude Code opening this repo: `CLAUDE.md` loads automatically, then read
`docs/PROJECT-STATE.md` before doing anything. **Do not infer project status from the
file tree** — several files look complete and are deliberately hypotheses.

If you are a human handing this to Claude Code for the first time: open
[docs/PROMPTS.md](docs/PROMPTS.md) and paste **P1 — Onboarding** as your first message.
It makes the session read the right files in the right order, verify the toolchain on
your machine, report what is missing, and then stop for your decisions.

---

## Current status in one paragraph

Phase 0.5 is complete: five context-building tools (3,465 lines) are built and verified
offline against synthetic fixtures. **No Android device has ever been connected**, so
nothing has touched the real app. Everything in `context/` is a hypothesis awaiting a
first crawl. Phase 1 execution tooling, the pytest layer, templates and 12 of 13 agents
are not built. Full detail in [docs/PROJECT-STATE.md](docs/PROJECT-STATE.md).

---

## The four rules

1. **Evidence over inference.** If it cannot be evidenced, it is written
   `UNKNOWN — needs manual verification`. Never guessed.
2. **Determinism in Python, judgment in the model.** If being wrong would be *invisible*,
   it is code, not a prompt.
3. **Human gates on anything that leaves the system.** Test cases are Testmo **drafts**.
   Healed locators are **diffs**. Bug reports are **proposals**. Agents never file
   tickets — a human does, in ClickUp.
4. **Fail loud.** No silent retries. No auto-healing that hides a regression.

---

## ⚠ Before you drive the app

The app under test is **production**, signed in with a **real account**. Tapping a
contact-agent control **sends a real, billable lead to a real Dubai estate agency**.

Every tap in `crawler.py` and `prober.py` passes through `tools/crawl_safety.py`. There
is no second tap path and no flag that disables the blocklist.

**Run this before every crawl session:**

```bash
python tools/crawl_safety.py selftest        # must be 119/119
```

And confirm the guard against the known-dangerous fixture:

```bash
python tools/crawl_safety.py --app-package com.bayut.app check \
    --page-source tests/fixtures/page_source/02-listing-detail.xml
```

Call, WhatsApp, Email, Share and Report must all show **BLOCK**. If they do not, stop.

---

## Quick start

Full instructions in [docs/SETUP.md](docs/SETUP.md). The short version:

```bash
# 1. install
npm install -g appium && appium driver install uiautomator2
python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt

# 2. configure
cp .env.example .env        # fill in; never commit this file

# 3. verify with no device — all four must pass
python tools/crawl_safety.py selftest
python tools/prober.py selftest
python tools/crawler.py offline --fixtures-dir tests/fixtures/page_source --out /tmp/check
python tools/crawl_safety.py --app-package com.bayut.app check \
    --page-source tests/fixtures/page_source/02-listing-detail.xml
```

---

## The tools

Every tool has `--help`, type hints, real error handling, and runs **without a device**
when given fixture paths.

| Tool | What it does | Verify it |
|---|---|---|
| [`pagesource.py`](tools/pagesource.py) | XML → elements, locators, stability, fingerprints | `parse`, `fingerprint`, `diff` |
| [`crawl_safety.py`](tools/crawl_safety.py) | The tap guard. 19 block + 10 allow rules, EN & AR | `selftest` → 119/119 |
| [`adb.py`](tools/adb.py) | Device, app state, locale, deep links, proxy, capture | `--dry-run` on any subcommand |
| [`crawler.py`](tools/crawler.py) | PASSIVE crawl → 7 context reports | `offline`, `plan` |
| [`prober.py`](tools/prober.py) | PROBE P1–P7 → filter behaviour from count deltas | `selftest` → 28/28 |

Phase 1 tools (`pairwise`, `testmo_client`, `clickup_client`, `evidence`, `oracle`,
`har_diff`) are **not built yet**. `oracle.py` and `har_diff.py` deliberately wait on the
first crawl — it decides whether traffic is interceptable and whether exact listing-ID
matching is possible. Building them now means guessing.

---

## Workflows

### First crawl (once, then per build)

```bash
appium --port 4723 &
mitmdump -w runs/crawl-01/capture.flow &
python tools/adb.py prepare
python tools/adb.py proxy set --host $MITM_HOST --port 8080
python tools/crawl_safety.py selftest

python tools/crawler.py crawl \
    --package $BAYUT_APP_PACKAGE --locale en-AE \
    --mitm-flow-file runs/crawl-01/capture.flow \
    --out context --artifacts runs/crawl-01
```

**Watch the first five minutes** for the certificate-pinning verdict — it decides whether
the API oracle can exist at all. Then read, in order:

1. `context/pinning-check.md`
2. `context/listing-id-visibility.md`
3. `context/crawl-uncertain.md`

### Expanding crawl reach

The first crawl runs STRICT, so most elements come back UNCERTAIN and untapped. That is
by design. To go deeper:

```bash
cp context/crawl-allowlist.example.yaml context/crawl-allowlist.yaml
# review context/crawl-uncertain.md; for each element decide allow / block / leave
python tools/crawl_safety.py --config context/crawl-allowlist.yaml selftest
python tools/crawler.py --safety-config context/crawl-allowlist.yaml crawl ...
```

The YAML can only **add** rules. There is no way to remove a default block rule from
config — that requires a code change, in review.

### Probing filter behaviour

```bash
cp context/probe-plan.example.yaml context/probe-plan.yaml
# fill every TODO from context/element-inventory.json — never from memory or the web app
python tools/prober.py validate-plan --plan context/probe-plan.yaml
python tools/prober.py run --plan context/probe-plan.yaml \
    --probes P1,P2,P3,P4 --package $BAYUT_APP_PACKAGE
```

Then update the YAML block in `context/filter-inventory.md` with the observed verdicts,
tagged `[OBSERVED <date> build <n>]`, and **delete every constraint marked
CONSTRAINT_WRONG**.

### Per-build drift detection

Re-run the crawl each build and diff. Changed accessibility ids break tests *silently* —
catching them before the suite goes red turns a mystery failure into a known change.

```bash
python tools/pagesource.py diff --mode structural \
    --baseline context/page_source/<old>.xml \
    --candidate context/page_source/<new>.xml
```

Exit code 1 means identifiers were **removed** — the ones that break existing tests.

---

## Repository layout

```
bayut-qa/
├── CLAUDE.md              project brief — loads in every Claude Code session
├── README.md              this file
├── context/               ground truth about the app (outputs of app-cartographer)
├── .claude/agents/        agent definitions
├── tools/                 deterministic CLIs
├── tests/
│   ├── conftest.py            PLACEHOLDER — raises until Phase 2
│   ├── screen_objects/        page objects, explicit waits only
│   ├── suites/                test suites by feature area
│   └── fixtures/              synthetic page sources for offline testing
├── templates/             BUG / TEST-DEFECT / CHARTER / EOD (pending)
├── runs/                  per-run artifacts
├── reports/               generated Markdown awaiting human review
└── docs/                  SETUP · ARCHITECTURE · PROJECT-STATE · DECISIONS
```

---

## Conventions

- **`com.bayut.app` is a placeholder**, not a verified package name. Get the real one
  from `adb shell pm list packages | grep -i bayut`.
- Anything unverified is tagged `[ASSUMED — verify]`; anything unanswerable,
  `UNKNOWN — needs manual verification`; anything a crawl confirmed,
  `[OBSERVED <date> build <n>]`.
- No `sleep()` in test code. Explicit waits only.
- Locator priority: `accessibility id` → `resource-id` → `uiautomator` → XPath last, with
  a logged warning on every XPath use.
- Secrets and machine-specific values live in `.env`, never inline.
- Every non-obvious design choice goes in `docs/DECISIONS.md`, append-only.
- Every tool ships a `selftest` or a fixture-based offline mode.

---

## Contributing

1. Read `docs/PROJECT-STATE.md`.
2. Make the change. Add a fixture or selftest assertion covering it.
3. Re-run all four verification commands above.
4. Update `docs/PROJECT-STATE.md` — the status tables **and** the session log — in the
   same commit.
5. If the change was a design decision, append to `docs/DECISIONS.md` with rationale and
   consequence.

Changes to `tools/crawl_safety.py` deserve extra care: the blocklist is the only control
preventing real leads reaching real agencies. Never widen it for convenience, and never
remove a rule without a reviewed reason.
