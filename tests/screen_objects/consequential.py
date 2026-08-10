"""Deliberate, non-gated taps.

The shared `crawl_safety` policy permanently and correctly refuses a small set of
actions (BLOCK-LOGOUT, BLOCK-LEAD-EMAIL/CALL/WHATSAPP, BLOCK-SHARE, ...) — that refusal
is not a bug to work around from inside a test. But a small number of human-reviewed,
narrowly-scoped tests genuinely need to perform one of these on purpose: verifying the
lead pipeline actually marks a listing Contacted, or that sign-out/sign-in actually
works, are real regression requirements a permanently-BLOCKing gate can never satisfy by
design (see docs/DECISIONS.md D-019).

`deliberate_tap()` is the one function outside `screen_objects/base.py::safe_tap()`
allowed to call `.click()` directly. It cannot be called quietly: it requires a `reason`,
and it always screenshots and logs before tapping — the same evidence discipline
CLAUDE.md requires of every consequential action in `tools/crawler.py`.

Nothing outside a `tests/suites/*/consequential/` folder may import this module. That
boundary is enforced by file layout and this docstring, not by code — keep it that way.
Never import this from `screen_objects/base.py` or any non-consequential screen object.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

RUNS_DIR = Path(os.environ.get("RUNS_DIR", "runs"))
EVIDENCE_DIR = RUNS_DIR / "consequential-evidence"


def deliberate_tap(driver, web_element, *, reason: str, evidence_tag: str) -> None:
    if not reason.strip():
        raise ValueError("deliberate_tap requires a non-empty reason — every call site "
                          "must justify itself, not just tap")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.time()
    shot_path = EVIDENCE_DIR / f"{int(timestamp)}-{evidence_tag}.png"
    driver.get_screenshot_as_file(str(shot_path))
    with open(EVIDENCE_DIR / "log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "tag": evidence_tag, "reason": reason,
            "screenshot": str(shot_path), "at": timestamp,
        }) + "\n")
    web_element.click()
