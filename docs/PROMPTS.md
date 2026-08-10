# Prompts

Copy-paste prompts for Claude Code sessions on this repo. Each block is self-contained —
paste it as the first message of a fresh session and nothing else is needed.

**Why these exist.** `CLAUDE.md` loads automatically and tells Claude the rules, but it
does not tell Claude *what to do this session*. These do. They also force a read of the
right files in the right order, which is what keeps a session from confidently building
on the parts of this repo that are still hypotheses.

**How to pick one:**

| Situation | Use |
|---|---|
| First time on this repo, any machine | **P1 — Onboarding** |
| Setting up a machine from scratch | P2 — Environment setup |
| A device is attached, ready to crawl | P3 — First crawl |
| A crawl just finished | P4 — Post-crawl review |
| Want the next crawl to reach further | P5 — Expand reach |
| Ready to determine filter behaviour | P6 — Probe session |
| No device, want to make progress | P7 — Build a Phase 1 tool |
| Phase 3 | P8 — Write an agent |
| A new app build shipped | P9 — Drift check |

---

## P1 — Onboarding (start here)

The one to hand a new QA engineer, or to paste when opening this repo on a new machine.

```text
You are picking up an existing QA automation project. Orient yourself before doing
anything else.

Read these, in this order:
  1. CLAUDE.md                    — constraints and rules, binding
  2. docs/PROJECT-STATE.md        — what is real vs. what is a hypothesis
  3. docs/ARCHITECTURE.md         — how the system works and why
  4. .claude/agents/README.md     — which agents exist, which are pending
  5. docs/GUARDRAILS.md           — production policy: environment, data, leads. BINDING
  6. context/regression-checklist.md — the team's own checklist; evidence, not guesswork
  7. docs/DECISIONS.md            — why things were decided the way they were

Critical: do NOT infer project status from the file tree. Roughly half of what looks
finished is deliberately a hypothesis awaiting verification against the real app.
docs/PROJECT-STATE.md section 3 lists exactly which files those are. Treat anything
tagged [ASSUMED — verify] or UNKNOWN as not yet true.

Then verify the toolchain actually works on this machine. Run all four and show me the
real output — do not summarise, do not assume:

  python tools/crawl_safety.py selftest
  python tools/prober.py selftest
  python tools/crawler.py offline --fixtures-dir tests/fixtures/page_source --out /tmp/check
  python tools/crawl_safety.py --app-package com.bayut.app check \
      --page-source tests/fixtures/page_source/02-listing-detail.xml

Expected: 119/119, 28/28, 3 screens with 12 blocked, and Call/WhatsApp/Email/Share/Report
all showing BLOCK (plus Save property as PROD-BLOCK-FAVOURITE, since the environment
defaults to production). If the fourth does not show all five as BLOCK, say so loudly and stop
— that guard is the only thing preventing real leads being sent to real estate agencies.

Also check the environment and tell me what is missing:
  - python --version (need 3.11+)
  - adb version, and whether any device is connected (adb devices -l)
  - appium --version (need 3.x) and appium driver list --installed (need uiautomator2)
  - whether .env exists, and which required variables are still blank

Then report back:
  1. Toolchain status — pass/fail per command, with the real numbers
  2. Environment gaps — what is not installed or not configured
  3. Where the project stands, in your own words
  4. The open decisions from PROJECT-STATE.md section 5 that need a human
  5. What you recommend doing next, and why

Then STOP and wait for me. Do not start building, do not modify context/ files, and do
not run anything against a device. Several decisions in section 5 are mine to make and
would change what you build.
```

---

## P2 — Environment setup on a new machine

```text
Set up this repo on this machine so it can run. Follow docs/SETUP.md.

Work through it and tell me what you did:
  1. Check prerequisites (Python 3.11+, Node 18+, Java JDK 11+, adb, git). Report which
     are missing rather than installing anything system-wide without asking.
  2. Create the .venv and install requirements.txt into it.
  3. Copy .env.example to .env if it does not exist. Do NOT invent any values — list
     which variables I still need to fill in and where each value comes from.
  4. Run the four verification commands from docs/SETUP.md section 5 and show real output.

Do not install Appium or Android platform-tools globally without asking me first.
Do not touch a device.

If anything fails, diagnose it against the troubleshooting table at the end of
docs/SETUP.md before proposing a fix.
```

---

## P3 — First crawl (a device is attached)

```text
We are ready to run the first PASSIVE crawl against the real Bayut Android app.

Read first: CLAUDE.md, docs/PROJECT-STATE.md, .claude/agents/app-cartographer.md —
especially the SAFETY section.

Before anything touches the device:
  1. python tools/crawl_safety.py selftest      — must be 119/119, otherwise STOP
  2. adb devices -l                             — exactly one device, state "device"
  3. Get the real package name: adb shell pm list packages | grep -i bayut
     Note: com.bayut.app throughout this repo is a PLACEHOLDER, not verified.
  4. python tools/adb.py prepare
  5. python tools/adb.py info --package <real package>  — record the build version

Then set up interception BEFORE crawling, so the pinning watchdog has something to watch:
  6. Start mitmdump writing to runs/crawl-01/capture.flow
  7. python tools/adb.py proxy set --host $MITM_HOST --port 8080
  8. Confirm the CA certificate is installed on the device

Then crawl, STRICT mode, en-AE:
  python tools/crawler.py crawl --package <real package> --locale en-AE \
      --mitm-flow-file runs/crawl-01/capture.flow \
      --out context --artifacts runs/crawl-01

Watch the first five minutes for the certificate-pinning verdict and tell me the moment
it appears — do not wait for the crawl to finish. If it reports PINNING_SUSPECTED, stop
and tell me, because that decides whether oracle.py can exist at all.

Rules for this session:
  - STRICT mode only. Do not pass --allow-uncertain-taps.
  - Never bypass or widen the safety blocklist, for any reason.
  - If something is ambiguous, stop and ask. A missed screen is cheap.
  - Report only what you observed. Anything you did not see is UNRESOLVED.
```

---

## P4 — Post-crawl review

```text
A crawl just finished. Interpret the results — do not act on them yet.

Read, in this order, and tell me what each one means for the programme:
  1. context/pinning-check.md          — can the API oracle exist at all?
  2. context/listing-id-visibility.md  — exact ID matching, or degrade to fuzzy?
  3. context/crawl-uncertain.md        — what did STRICT mode refuse to touch?
  4. context/crawl-blocked.md          — which consequential controls exist in this app?
  5. context/locator-quality.md        — how bad is the testID situation?
  6. context/screen-inventory.observed.md and context/screen-graph.mermaid

Then compare what was observed against what we assumed:
  - Which lines in context/feature-map.md and context/filter-inventory.md are now
    confirmed, and which are contradicted?
  - Which [ASSUMED — verify] tags can become [OBSERVED <date> build <n>]?
  - What did we assume exists that does not, and vice versa?

Then tell me:
  1. The three findings that most change our plan
  2. What is still UNRESOLVED and what it would take to resolve each
  3. Whether oracle.py is buildable, and in which form
  4. What you would do next

Do not edit context/ files yet — propose the changes and let me approve them.
```

---

## P5 — Expand crawl reach

```text
The first STRICT crawl left many elements UNCERTAIN and untapped. Let us safely widen
what the crawler is allowed to touch.

Read context/crawl-uncertain.md and .claude/agents/app-cartographer.md (SAFETY section).

For each distinct uncertain element, recommend one of:
  - ALLOW  — safe navigation or read-only. Say why it has no outward effect.
  - BLOCK  — consequential. Say what the consequence is.
  - LEAVE  — genuinely unclear. Leaving it uncertain is a valid answer.

Be conservative. Anything that could contact an agent, submit a form, delete data, reach
a moderation queue, spend money, opt into notifications, or leave the app is BLOCK. If
you cannot tell what an element does from its identifier and screenshot, it is LEAVE.

Then draft context/crawl-allowlist.yaml from the ALLOW and BLOCK decisions, using
context/crawl-allowlist.example.yaml as the format. Remember the config can only ADD
rules — there is no way to remove a default block rule from YAML, by design.

Verify before I approve:
  python tools/crawl_safety.py --config context/crawl-allowlist.yaml selftest
  python tools/crawl_safety.py --config context/crawl-allowlist.yaml check \
      --page-source context/page_source/<a real dump>.xml

Show me the diff in verdicts the new rules produce. Then stop — I will approve before
any re-crawl.
```

---

## P6 — Probe session (filter behaviour)

```text
Time to determine the app's actual filter behaviour by experiment.

Read: .claude/agents/app-cartographer.md (MODE 2 — PROBE), docs/ARCHITECTURE.md section 6,
and context/filter-inventory.md (the current hypotheses).

First build the probe plan:
  1. Copy context/probe-plan.example.yaml to context/probe-plan.yaml
  2. Fill every TODO from context/element-inventory.json — the OBSERVED locators only.
     Never from memory, never from the Bayut web app, never guessed.
  3. Identify the result-count element precisely. If it is wrong, every verdict in
     filter-behaviour.md will be wrong in the same direction.
  4. python tools/prober.py validate-plan --plan context/probe-plan.yaml

Then run P1 through P4:
  python tools/prober.py run --plan context/probe-plan.yaml --probes P1,P2,P3,P4 \
      --package <real package>

Then interpret context/filter-behaviour.md for me. Pay particular attention to P4 —
PREVENTED, ALLOWED_EMPTY and CONSTRAINT_WRONG must stay strictly distinct. Treating an
ALLOWED_EMPTY as a constraint deletes that combination from every generated suite
forever, and the suite still looks full.

Then propose (do not apply) an updated YAML parameter block for
context/filter-inventory.md:
  - every verdict tagged [OBSERVED <date> build <n>]
  - every CONSTRAINT_WRONG constraint deleted
  - every ALLOWED_EMPTY moved out of constraints and into the test-case notes
  - anything UNRESOLVED left UNRESOLVED, with what it would take to settle it
```

---

## P7 — Build a Phase 1 tool (no device needed)

```text
Build <pairwise.py | testmo_client.py | clickup_client.py | evidence.py> in tools/.

Read first: CLAUDE.md, docs/PROJECT-STATE.md section 2, docs/ARCHITECTURE.md, and an
existing tool for house style — tools/crawl_safety.py is the best reference.

Requirements, matching the existing tools:
  - Standalone CLI with --help, subcommands, type hints, real error handling
  - No stubs, no pass bodies
  - Runs and is testable WITHOUT a device or live credentials: takes fixture paths as
    arguments, and ships either a selftest subcommand or a fixture-based offline mode
  - Fails loudly with actionable messages; never returns a silent default
  - Any value it needs that we do not have goes in .env.example and is referenced by
    name, never inlined

Tool-specific hard rules:
  - pairwise.py     — wraps allpairspy. Must report row count and coverage stats so an
                      over-broad constraint is visible. This is the tool that exists so a
                      model never does combinatorics.
  - clickup_client.py — READ-ONLY BY CONSTRUCTION. No create or update method may exist
                      in the file at all. Not disabled, not flag-guarded: absent. See
                      D-004 in docs/DECISIONS.md.
  - testmo_client.py  — generated cases are pushed as DRAFTS only.
  - evidence.py     — trims logcat to the failure window, filters noise, extracts HAR
                      entries, emits an evidence bundle JSON good enough for
                      bug-report-writer to work from with no extra input.

Do NOT build oracle.py or har_diff.py. Their design depends on crawl outputs we do not
have yet — whether traffic is interceptable, and whether exact listing-ID matching is
possible. Guessing means rewriting the most valuable check in the system.

When done: add fixtures under tests/fixtures/, prove it works against them with real
output, and update docs/PROJECT-STATE.md sections 1 and 2 plus the session log.
```

---

## P8 — Write an agent

```text
Write .claude/agents/<name>.md.

Read first: CLAUDE.md, .claude/agents/README.md (for the spec and inherited hard rules),
and .claude/agents/app-cartographer.md as the reference for depth and structure.

Format:
  - YAML frontmatter: name, description (written so a dispatcher can route to it), tools
    (least privilege — do not grant Write to an agent that only reads)
  - Body: Inputs → Procedure (numbered, concrete) → Output format → Hard rules
  - Depth of a real runbook, not a paragraph. Where a step needs a decision, say what
    evidence settles it.

Inherited rules that apply even if unstated in the file:
  - Never file a ticket. Output is unverified Markdown in reports/.
  - Evidence over inference. No evidence means UNKNOWN — needs manual verification.
  - Never read the app source. context/ is the only source of truth about the app.
  - Never do combinatorics — call pairwise.py.
  - If evidence contradicts the test's own assertion, produce a TEST DEFECT report, not
    a bug report.
  - Any agent driving a device taps only through tools/crawl_safety.py.

If you are writing failure-triage: it gets the most rigorous spec of the set, because it
decides whether this programme survives. Document the classification rules as an explicit
decision table covering REAL DEFECT / TEST DEFECT / LOCATOR DRIFT / ENVIRONMENT / DATA /
FLAKE, and state which evidence settles each branch.

Then update .claude/agents/README.md to move it from "specified" to "built".
```

---

## P9 — Per-build drift check

```text
A new Bayut build shipped. Detect what changed before it breaks the suite.

Read: .claude/agents/app-cartographer.md (Re-running section).

  1. python tools/adb.py info --package <real package>   — record the new build version
  2. python tools/crawl_safety.py selftest               — 119/119 or stop
  3. Re-run the crawl into a fresh output directory, same locale and settings as the
     baseline so the comparison is fair
  4. Diff structurally against the previous dumps:
     python tools/pagesource.py diff --mode structural \
         --baseline context/page_source/<old>.xml --candidate <new>.xml

Report as context/drift-report.md:
  - New screens or elements
  - REMOVED elements — these are the likely cause of upcoming locator failures
  - CHANGED accessibility ids — flag these loudly, they break tests silently
  - Behavioural changes, if the probes were re-run

Frame each as a contract change first, not a defect. The dev team may have shipped it
deliberately. Our job is to notice before it surprises us in production.
```

---

## Writing your own prompts for this repo

What makes these work, if you need a new one:

1. **Name the files to read, in order.** Left to itself a session reads the file tree and
   builds on hypotheses as though they were facts.
2. **Say what not to assume.** "Do not infer status from the file tree" earns its place
   in almost every prompt here.
3. **Demand real output, not a summary.** "Show me the real output — do not summarise"
   prevents a plausible-sounding report of a command that was never run.
4. **End with a stop.** Setup and review prompts finish with "then STOP and wait for me".
   The open decisions in `docs/PROJECT-STATE.md` section 5 are human calls.
5. **Restate the safety rule whenever a device is involved.** It costs three lines and
   the failure mode is sending real leads to real estate agencies.
6. **Ask for UNRESOLVED explicitly.** Otherwise gaps get filled with something plausible
   rather than being reported as gaps.
