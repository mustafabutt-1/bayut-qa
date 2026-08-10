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
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from crawl_safety import LeadNotAuthorised, SafetyPolicy  # noqa: E402
from pagesource import parse_page_source  # noqa: E402

RUNS_DIR = Path(os.environ.get("RUNS_DIR", "runs"))
EVIDENCE_DIR = RUNS_DIR / "consequential-evidence"


def _assert_lead_allowed(driver, policy: SafetyPolicy, evidence_tag: str) -> str:
    """Refuse a lead tap unless an allowlisted agency is on the screen right now.

    The individual lead tests already navigate to the sanctioned test agency and assert
    its name — but that assertion lives in the test, so a new test that forgets it would
    get no protection at all. Re-checking here means the guarantee belongs to the tap,
    not to the caller's discipline. The check reads the live page source itself; it does
    not accept the caller's word for which agency is on screen.
    """
    auth = policy.authorise_lead(parse_page_source(driver.page_source))
    if not auth.allowed:
        raise LeadNotAuthorised(
            f"deliberate_tap({evidence_tag!r}) targets a lead action, but "
            f"{auth.reason}"
        )
    return auth.agency_seen or "UNKNOWN"


def _is_lead_action(driver, web_element, policy: SafetyPolicy, evidence_tag: str) -> bool:
    """Is the element about to be tapped a lead-contact control?

    Classifies the *exact* element being clicked, matched on its resource-id, per D-024
    and D-034 — never a lookalike found by a separate search. Classification is
    best-effort because a driver call can fail mid-flow; the ``evidence_tag`` check is
    the deliberate backstop, since every lead call site already tags itself as one.
    """
    if "lead" in evidence_tag.lower():
        return True
    try:
        resource_id = web_element.get_attribute("resource-id")
        if not resource_id:
            return False
        for el in parse_page_source(driver.page_source):
            if el.resource_id == resource_id:
                return policy.evaluate(el).category == "lead_contact"
    except Exception:
        return False
    return False


def deliberate_tap(driver, web_element, *, reason: str, evidence_tag: str,
                   policy: SafetyPolicy | None = None) -> None:
    if not reason.strip():
        raise ValueError("deliberate_tap requires a non-empty reason — every call site "
                          "must justify itself, not just tap")

    # Classify the exact element about to be tapped (D-024/D-034: classification must
    # target the element that gets clicked, never a lookalike). If it is a lead action,
    # the agency allowlist applies here too — deliberate_tap is an exception to the
    # *refusal*, not to the *verification*.
    policy = policy or SafetyPolicy(app_package=os.environ.get("BAYUT_APP_PACKAGE"))
    agency_seen = None
    if _is_lead_action(driver, web_element, policy, evidence_tag):
        agency_seen = _assert_lead_allowed(driver, policy, evidence_tag)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.time()
    shot_path = EVIDENCE_DIR / f"{int(timestamp)}-{evidence_tag}.png"
    driver.get_screenshot_as_file(str(shot_path))
    with open(EVIDENCE_DIR / "log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "tag": evidence_tag, "reason": reason,
            "screenshot": str(shot_path), "at": timestamp,
            "lead_agency_verified": agency_seen,
        }) + "\n")
    web_element.click()
