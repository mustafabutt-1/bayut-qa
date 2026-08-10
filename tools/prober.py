"""PROBE mode: determine the app's *behavioural* rules by experiment, not by asking.

A passive crawl tells you a filter exists. It cannot tell you whether amenities are
AND-ed or OR-ed, whether property type is single- or multi-select, or whether a
constraint is genuinely prevented or merely returns nothing. Those are answered by
changing one thing and reading the result count.

**The result count is the instrument.** Every probe: set a known state, read the count,
change one thing, read the count, infer from the delta — and record the raw numbers so a
human can audit the inference.

Every tap goes through ``crawl_safety.SafetyPolicy``, same as the crawler.

The inference math is pure and has a ``selftest``, so it can be verified with no device.

CLI
---
    python tools/prober.py selftest
    python tools/prober.py infer and-or --count-a 812 --count-b 204 --count-ab 96
    python tools/prober.py infer constraint --selectable --count 0
    python tools/prober.py validate-plan --plan context/probe-plan.yaml
    python tools/prober.py run --plan context/probe-plan.yaml --probes P1,P3,P4
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crawl_safety import SafetyPolicy
from pagesource import Element, parse_page_source

MIN_ACTION_INTERVAL_S = 0.8
PROBE_ACTION_CAP = 400

# Arabic-Indic and Eastern Arabic-Indic digits, so counts parse in ar-AE.
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def parse_count(text: str) -> int | None:
    """Extract a result count from a label like '1,247 properties' or '١٬٢٤٧ عقار'.

    Returns None when no number is present — the caller must treat that as UNRESOLVED,
    never as zero. A missing count and a genuine zero mean completely different things.
    """
    if not text:
        return None
    normalised = text.translate(_DIGIT_MAP).replace("٬", ",").replace("،", ",")
    match = re.search(r"\d[\d,\s]*", normalised)
    if not match:
        return None
    digits = re.sub(r"[^\d]", "", match.group(0))
    return int(digits) if digits else None


# ---------------------------------------------------------------------------
# Inference — pure functions. Every one returns (verdict, rationale).
# ---------------------------------------------------------------------------


@dataclass
class Inference:
    verdict: str
    rationale: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_cardinality(a_still_selected: bool, count_changed: bool,
                      applied_live: bool = True) -> Inference:
    """P1 — select A, then select B without deselecting A."""
    ev = {"a_still_selected": a_still_selected, "count_changed": count_changed,
          "applied_live": applied_live}
    if not a_still_selected:
        return Inference("SINGLE_SELECT",
                         "Selecting B deselected A, so the control holds one value.", ev)
    if count_changed:
        return Inference("MULTI_SELECT",
                         "A stayed selected and the count moved, so both values are applied.", ev)
    if not applied_live:
        return Inference("UNRESOLVED",
                         "A stayed selected but the count did not move, and the filter is not "
                         "applied live. Re-probe after tapping apply — this is inconclusive, "
                         "not evidence of single-select.", ev)
    return Inference("MULTI_SELECT_NO_EFFECT",
                     "A stayed selected and the count did not move even though filters apply "
                     "live. Either B adds nothing to the result set, or the second selection "
                     "is not reaching the query. Re-probe with a value known to change the "
                     "count before concluding.", ev)


def infer_apply_mode(count_changed: bool, button_label_changed: bool) -> Inference:
    """P2 — change one filter, then wait without tapping apply."""
    ev = {"count_changed": count_changed, "button_label_changed": button_label_changed}
    if count_changed:
        return Inference("LIVE", "The result count updated without an explicit apply.", ev)
    if button_label_changed:
        return Inference("DEFERRED_LIST_LIVE_COUNT",
                         "The apply button's label updated but the list did not. The count is "
                         "queried live; the list is deferred until apply.", ev)
    return Inference("EXPLICIT_APPLY",
                     "Nothing changed until apply was tapped. Intermediate assertions on the "
                     "result set are illegal before apply — tests must not check early.", ev)


def infer_and_or(count_a: int, count_b: int, count_ab: int) -> Inference:
    """P3 — two options within one multi-select filter."""
    ev = {"count_a": count_a, "count_b": count_b, "count_ab": count_ab,
          "min": min(count_a, count_b), "max": max(count_a, count_b)}
    lo, hi = min(count_a, count_b), max(count_a, count_b)
    if count_ab <= lo:
        return Inference("AND",
                         f"Combined count {count_ab} <= min({count_a},{count_b})={lo}. "
                         f"Selecting both narrows the set, so the options intersect.", ev)
    if count_ab >= hi:
        return Inference("OR",
                         f"Combined count {count_ab} >= max({count_a},{count_b})={hi}. "
                         f"Selecting both widens the set, so the options union.", ev)
    return Inference("UNRESOLVED",
                     f"Combined count {count_ab} sits strictly between {lo} and {hi}, which "
                     f"neither AND nor OR predicts. Possible causes: result caps, "
                     f"deduplication, relevance trimming, or a stale count. Record the raw "
                     f"numbers and re-probe with a different pair before concluding.", ev)


def infer_constraint(selectable: bool, count: int | None) -> Inference:
    """P4 — attempt a supposedly-invalid combination.

    Conflating PREVENTED with ALLOWED_EMPTY silently deletes valid coverage from every
    generated suite, so these are kept strictly distinct.
    """
    ev = {"selectable": selectable, "count": count}
    if not selectable:
        return Inference("PREVENTED",
                         "The option is greyed out or untappable in this combination. This is "
                         "a real pairwise constraint — keep it.", ev)
    if count is None:
        return Inference("UNRESOLVED",
                         "The combination was selectable but no result count could be read. "
                         "Do not guess: re-probe.", ev)
    if count == 0:
        return Inference("ALLOWED_EMPTY",
                         "Selectable and returns zero results. This is a **valid test case** "
                         "(empty-state coverage), NOT a constraint. Remove it from the "
                         "constraint list or the generator will never produce it.", ev)
    return Inference("CONSTRAINT_WRONG",
                     f"Selectable and returns {count} results. The proposed constraint is "
                     f"false — delete it, and check what else was excluded on the same "
                     f"assumption.", ev)


def infer_boundary(boundary_value: float, returned_at_boundary: bool,
                   count_at: int | None, count_just_below: int | None) -> Inference:
    """P6 — is a range filter's max inclusive?"""
    ev = {"boundary": boundary_value, "returned_at_boundary": returned_at_boundary,
          "count_at_boundary": count_at, "count_just_below": count_just_below}
    if returned_at_boundary:
        return Inference("INCLUSIVE",
                         f"An item priced exactly at {boundary_value} is returned when max = "
                         f"{boundary_value}.", ev)
    return Inference("EXCLUSIVE_SUSPECTED",
                     f"An item known to sit exactly at {boundary_value} was NOT returned with "
                     f"max = {boundary_value}. If the UI labels the filter 'up to', this is a "
                     f"defect: a user searching up to their exact budget loses every listing "
                     f"priced at it. Confirm against the API response before reporting.", ev)


def infer_persistence(before: dict[str, Any], after: dict[str, Any], scenario: str) -> Inference:
    ev = {"scenario": scenario, "before": before, "after": after}
    lost = [k for k, v in before.items() if after.get(k) != v]
    if not lost:
        return Inference("RETAINED", f"All filters survived: {scenario}.", ev)
    return Inference("LOST",
                     f"Filters changed after {scenario}: {lost}. Losing applied filters on "
                     f"back-navigation is the most commonly reported defect class in property "
                     f"portals — verify against the AC before filing.", ev)


# ---------------------------------------------------------------------------
# Probe plan
# ---------------------------------------------------------------------------

_REQUIRED_PLAN_KEYS = ("count_element", "filters")
_VALID_STRATEGIES = ("accessibility id", "resource-id", "uiautomator", "xpath")


@dataclass
class Locator:
    strategy: str
    value: str

    @classmethod
    def parse(cls, raw: Any, where: str) -> "Locator":
        if not isinstance(raw, dict) or "strategy" not in raw or "value" not in raw:
            raise ValueError(f"{where}: locator needs 'strategy' and 'value'")
        if raw["strategy"] not in _VALID_STRATEGIES:
            raise ValueError(f"{where}: strategy must be one of {_VALID_STRATEGIES}, "
                             f"got {raw['strategy']!r}")
        if raw["strategy"] == "xpath":
            print(f"warning: {where} uses XPath — fragile, expect drift", file=sys.stderr)
        return cls(str(raw["strategy"]), str(raw["value"]))


@dataclass
class FilterPlan:
    name: str
    options: dict[str, Locator]
    open: Locator | None = None
    apply: Locator | None = None
    reset: Locator | None = None


@dataclass
class ProbePlan:
    count_element: Locator
    filters: dict[str, FilterPlan]
    count_pattern: str = r"\d[\d,\s]*"
    source: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "ProbePlan":
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"probe plan not found: {p}")
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML is required to read a probe plan: pip install PyYAML") from exc
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        missing = [k for k in _REQUIRED_PLAN_KEYS if k not in data]
        if missing:
            raise ValueError(f"{p}: missing required keys: {missing}")
        filters: dict[str, FilterPlan] = {}
        for name, raw in (data.get("filters") or {}).items():
            options = raw.get("options") or {}
            if len(options) < 2:
                raise ValueError(f"{p}: filter {name!r} needs at least 2 options to probe")
            filters[name] = FilterPlan(
                name=name,
                options={k: Locator.parse(v, f"{p}:filters.{name}.options.{k}")
                         for k, v in options.items()},
                open=Locator.parse(raw["open"], f"{p}:filters.{name}.open") if raw.get("open") else None,
                apply=Locator.parse(raw["apply"], f"{p}:filters.{name}.apply") if raw.get("apply") else None,
                reset=Locator.parse(raw["reset"], f"{p}:filters.{name}.reset") if raw.get("reset") else None,
            )
        return cls(
            count_element=Locator.parse(data["count_element"], f"{p}:count_element"),
            filters=filters,
            count_pattern=str(data.get("count_pattern", r"\d[\d,\s]*")),
            source=str(p),
        )


# ---------------------------------------------------------------------------
# Live runner
# ---------------------------------------------------------------------------


@dataclass
class ProbeResult:
    probe: str
    subject: str
    inference: Inference
    raw: list[dict[str, Any]] = field(default_factory=list)
    at: str = field(default_factory=_now)


class Prober:
    """Drives the live app. Every tap is safety-gated, rate-limited and capped."""

    def __init__(self, plan: ProbePlan, policy: SafetyPolicy, driver: Any,
                 *, settle_s: float = 2.0, max_actions: int = PROBE_ACTION_CAP) -> None:
        self.plan = plan
        self.policy = policy
        self.driver = driver
        self.settle_s = settle_s
        self.max_actions = min(max_actions, PROBE_ACTION_CAP)
        self.actions = 0
        self.results: list[ProbeResult] = []
        self.refused: list[dict[str, Any]] = []

    # -- primitives ------------------------------------------------------

    def _elements(self) -> list[Element]:
        return parse_page_source(self.driver.page_source)

    def _find(self, loc: Locator) -> Element | None:
        for el in self._elements():
            if loc.strategy == "accessibility id" and el.content_desc == loc.value:
                return el
            if loc.strategy == "resource-id" and el.resource_id == loc.value:
                return el
            if loc.strategy == "uiautomator" and loc.value in (el.text, el.label):
                return el
            if loc.strategy == "xpath" and el.xpath == loc.value:
                return el
        return None

    def tap(self, loc: Locator, *, what: str) -> bool:
        """The only tap path. Refuses anything the safety policy will not allow."""
        if self.actions >= self.max_actions:
            raise RuntimeError(f"probe action cap reached ({self.max_actions})")
        el = self._find(loc)
        if el is None:
            return False
        allowed, decision = self.policy.may_tap(el)
        if not allowed:
            self.refused.append({"what": what, **decision.to_dict()})
            return False
        point = el.center
        if point is None:
            return False
        self.driver.tap([point], 100)
        self.actions += 1
        time.sleep(max(MIN_ACTION_INTERVAL_S, self.settle_s))
        return True

    def read_count(self) -> int | None:
        el = self._find(self.plan.count_element)
        if el is None:
            return None
        return parse_count(el.text or el.content_desc)

    def is_selected(self, loc: Locator) -> bool | None:
        el = self._find(loc)
        if el is None:
            return None
        return el.selected or el.checked

    def is_selectable(self, loc: Locator) -> bool | None:
        el = self._find(loc)
        if el is None:
            return None
        return el.enabled and el.clickable

    def reset(self, fp: FilterPlan) -> None:
        if fp.reset:
            self.tap(fp.reset, what=f"{fp.name}: reset")
        if fp.apply:
            self.tap(fp.apply, what=f"{fp.name}: apply")

    def _open(self, fp: FilterPlan) -> None:
        if fp.open:
            self.tap(fp.open, what=f"{fp.name}: open")

    # -- probes ----------------------------------------------------------

    def p1_cardinality(self, fp: FilterPlan) -> ProbeResult:
        raw: list[dict[str, Any]] = []
        self._open(fp)
        self.reset(fp)
        names = list(fp.options)[:2]
        a, b = fp.options[names[0]], fp.options[names[1]]
        self.tap(a, what=f"{fp.name}: select {names[0]}")
        count_a = self.read_count()
        raw.append({"step": f"select {names[0]}", "count": count_a})
        self.tap(b, what=f"{fp.name}: select {names[1]}")
        count_ab = self.read_count()
        a_still = self.is_selected(a)
        raw.append({"step": f"select {names[1]}", "count": count_ab, "a_still_selected": a_still})
        if a_still is None:
            inf = Inference("UNRESOLVED",
                            f"Could not read the selected state of {names[0]}. The option "
                            f"exposes neither `selected` nor `checked`, so cardinality cannot "
                            f"be determined from the UI — this is itself a testability finding.",
                            {"raw": raw})
        else:
            inf = infer_cardinality(a_still, count_a != count_ab,
                                    applied_live=count_a is not None and count_ab is not None)
        return ProbeResult("P1", fp.name, inf, raw)

    def p2_apply_mode(self, fp: FilterPlan) -> ProbeResult:
        raw: list[dict[str, Any]] = []
        self._open(fp)
        self.reset(fp)
        before = self.read_count()
        before_label = self._label(fp.apply) if fp.apply else None
        name = list(fp.options)[0]
        self.tap(fp.options[name], what=f"{fp.name}: select {name}")
        deadline = time.time() + 2.0
        after, after_label = before, before_label
        while time.time() < deadline:
            after = self.read_count()
            after_label = self._label(fp.apply) if fp.apply else None
            if after != before or after_label != before_label:
                break
            time.sleep(0.25)
        raw.append({"before_count": before, "after_count": after,
                    "before_label": before_label, "after_label": after_label})
        return ProbeResult("P2", fp.name,
                           infer_apply_mode(after != before, after_label != before_label), raw)

    def _label(self, loc: Locator | None) -> str | None:
        if loc is None:
            return None
        el = self._find(loc)
        return None if el is None else (el.text or el.content_desc)

    def p3_and_or(self, fp: FilterPlan) -> ProbeResult:
        raw: list[dict[str, Any]] = []
        names = list(fp.options)[:2]
        counts: list[int | None] = []
        for name in names:
            self._open(fp)
            self.reset(fp)
            self.tap(fp.options[name], what=f"{fp.name}: select {name}")
            if fp.apply:
                self.tap(fp.apply, what=f"{fp.name}: apply")
            c = self.read_count()
            counts.append(c)
            raw.append({"selection": [name], "count": c})
        self._open(fp)
        self.reset(fp)
        for name in names:
            self.tap(fp.options[name], what=f"{fp.name}: select {name}")
        if fp.apply:
            self.tap(fp.apply, what=f"{fp.name}: apply")
        count_ab = self.read_count()
        raw.append({"selection": names, "count": count_ab})
        if None in counts or count_ab is None:
            inf = Inference("UNRESOLVED",
                            "At least one result count could not be read. AND/OR cannot be "
                            "inferred from a missing count.", {"raw": raw})
        else:
            inf = infer_and_or(counts[0], counts[1], count_ab)  # type: ignore[arg-type]
        return ProbeResult("P3", fp.name, inf, raw)

    def p4_constraint(self, fp: FilterPlan, option_a: str, option_b: str,
                      constraint_id: str) -> ProbeResult:
        raw: list[dict[str, Any]] = []
        self._open(fp)
        self.reset(fp)
        self.tap(fp.options[option_a], what=f"{fp.name}: select {option_a}")
        selectable = self.is_selectable(fp.options[option_b])
        count: int | None = None
        if selectable:
            self.tap(fp.options[option_b], what=f"{fp.name}: select {option_b}")
            if fp.apply:
                self.tap(fp.apply, what=f"{fp.name}: apply")
            count = self.read_count()
        raw.append({"constraint": constraint_id, "a": option_a, "b": option_b,
                    "b_selectable": selectable, "count": count})
        if selectable is None:
            inf = Inference("UNRESOLVED", f"Option {option_b!r} was not present on screen.",
                            {"raw": raw})
        else:
            inf = infer_constraint(selectable, count)
        return ProbeResult("P4", f"{fp.name}: {constraint_id}", inf, raw)

    def p5_filter_existence(self, expected: list[str]) -> ProbeResult:
        present = sorted(self.plan.filters)
        missing = [f for f in expected if f not in present]
        extra = [f for f in present if f not in expected]
        verdict = "MATCHES" if not missing and not extra else "DIVERGES"
        inf = Inference(
            verdict,
            f"Filters in the plan but not in filter-inventory.md: {extra or 'none'}. "
            f"In filter-inventory.md but not found in the app: {missing or 'none'}. "
            f"Both directions are findings: an inventory filter that does not exist means "
            f"the hypothesis was wrong; an app filter nobody listed means untested surface.",
            {"expected": expected, "observed": present},
        )
        return ProbeResult("P5", "filter existence", inf,
                           [{"missing": missing, "extra": extra}])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_filter_behaviour(results: list[ProbeResult], refused: list[dict[str, Any]],
                           out_path: Path, meta: dict[str, Any]) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Filter Behaviour — Observed by Probe\n",
        "Generated by `tools/prober.py`. Every verdict below is followed by the raw counts "
        "that produced it, so the inference can be audited rather than trusted.\n",
        f"- Probed: {meta.get('started', 'UNKNOWN')}",
        f"- App: {meta.get('app', 'UNKNOWN')}",
        f"- Locale: {meta.get('locale', 'UNKNOWN')}",
        f"- Plan: `{meta.get('plan', 'UNKNOWN')}`",
        f"- Actions used: {meta.get('actions', 'UNKNOWN')}\n",
        "\n## Verdicts\n",
        "| Probe | Subject | Verdict | Rationale |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.probe} | {r.subject} | **{r.inference.verdict}** | "
                     f"{r.inference.rationale[:160]} |")

    lines.append("\n## Raw evidence\n")
    for r in results:
        lines.append(f"\n### {r.probe} — {r.subject}\n")
        lines.append(f"**{r.inference.verdict}** — {r.inference.rationale}\n")
        lines.append("```json")
        lines.append(json.dumps(r.raw, indent=2, ensure_ascii=False))
        lines.append("```")

    unresolved = [r for r in results if r.inference.verdict.startswith("UNRESOLVED")]
    lines.append("\n## Unresolved\n")
    if unresolved:
        for r in unresolved:
            lines.append(f"- **{r.probe} {r.subject}** — {r.inference.rationale}")
    else:
        lines.append("_Every probe reached a verdict._")

    lines.append("\n## Refused taps during probing\n")
    if refused:
        lines.append("The safety policy refused these. If a probe needed one of them, the "
                     "probe is incomplete — say so rather than working around the guard.\n")
        for x in refused:
            lines.append(f"- `{x.get('rule_id')}` on {x.get('element')} (during {x.get('what')})")
    else:
        lines.append("_None._")

    lines.append("\n## Next step\n")
    lines.append("Update the YAML parameter block in `context/filter-inventory.md` with these "
                 "verdicts, tagging each `[OBSERVED " + _now()[:10] +
                 " build <n>]`. Delete every constraint this run marked CONSTRAINT_WRONG, and "
                 "move every ALLOWED_EMPTY out of the constraint list and into the test cases "
                 "— those are empty-state coverage, not impossible combinations.\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Selftest — verifies the inference math with no device
# ---------------------------------------------------------------------------

_CASES: tuple[tuple[str, Inference, str], ...] = (
    ("P1 single-select", infer_cardinality(False, True), "SINGLE_SELECT"),
    ("P1 multi-select", infer_cardinality(True, True), "MULTI_SELECT"),
    ("P1 deferred", infer_cardinality(True, False, applied_live=False), "UNRESOLVED"),
    ("P1 no effect", infer_cardinality(True, False, applied_live=True), "MULTI_SELECT_NO_EFFECT"),
    ("P2 live", infer_apply_mode(True, False), "LIVE"),
    ("P2 deferred list", infer_apply_mode(False, True), "DEFERRED_LIST_LIVE_COUNT"),
    ("P2 explicit", infer_apply_mode(False, False), "EXPLICIT_APPLY"),
    ("P3 AND", infer_and_or(812, 204, 96), "AND"),
    ("P3 AND at boundary", infer_and_or(812, 204, 204), "AND"),
    ("P3 OR", infer_and_or(812, 204, 1016), "OR"),
    ("P3 OR at boundary", infer_and_or(812, 204, 812), "OR"),
    ("P3 impossible", infer_and_or(812, 204, 500), "UNRESOLVED"),
    ("P4 prevented", infer_constraint(False, None), "PREVENTED"),
    ("P4 allowed-empty", infer_constraint(True, 0), "ALLOWED_EMPTY"),
    ("P4 constraint wrong", infer_constraint(True, 43), "CONSTRAINT_WRONG"),
    ("P4 no count", infer_constraint(True, None), "UNRESOLVED"),
    ("P6 inclusive", infer_boundary(145000, True, 12, 11), "INCLUSIVE"),
    ("P6 exclusive", infer_boundary(145000, False, 11, 11), "EXCLUSIVE_SUSPECTED"),
    ("P7 retained", infer_persistence({"beds": "2"}, {"beds": "2"}, "back nav"), "RETAINED"),
    ("P7 lost", infer_persistence({"beds": "2"}, {"beds": "Any"}, "back nav"), "LOST"),
)

_COUNT_CASES: tuple[tuple[str, int | None], ...] = (
    ("1,247 properties", 1247),
    ("1 247 properties", 1247),
    ("Show 12 properties", 12),
    ("١٬٢٤٧ عقار", 1247),
    ("٥ عقارات", 5),
    ("0 properties", 0),
    ("No properties found", None),
    ("", None),
)


def run_selftest() -> int:
    failures: list[str] = []
    for name, inference, expected in _CASES:
        if inference.verdict != expected:
            failures.append(f"{name}: expected {expected}, got {inference.verdict}")
    for text, expected_count in _COUNT_CASES:
        got = parse_count(text)
        if got != expected_count:
            failures.append(f"parse_count({text!r}): expected {expected_count}, got {got}")
    total = len(_CASES) + len(_COUNT_CASES)
    print(f"selftest: {total - len(failures)}/{total} assertions passed")
    for f in failures:
        print(f"  FAIL  {f}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_inference(inf: Inference) -> int:
    print(f"verdict   : {inf.verdict}")
    print(f"rationale : {inf.rationale}")
    print(f"evidence  : {json.dumps(inf.evidence, ensure_ascii=False)}")
    return 0


def _cmd_infer(args: argparse.Namespace) -> int:
    if args.probe == "cardinality":
        return _print_inference(infer_cardinality(args.a_still_selected, args.count_changed,
                                                  applied_live=not args.not_live))
    if args.probe == "apply-mode":
        return _print_inference(infer_apply_mode(args.count_changed, args.label_changed))
    if args.probe == "and-or":
        return _print_inference(infer_and_or(args.count_a, args.count_b, args.count_ab))
    if args.probe == "constraint":
        return _print_inference(infer_constraint(args.selectable, args.count))
    if args.probe == "boundary":
        return _print_inference(infer_boundary(args.boundary, args.returned, args.count_at,
                                               args.count_below))
    raise ValueError(f"unknown probe {args.probe!r}")


def _cmd_validate_plan(args: argparse.Namespace) -> int:
    plan = ProbePlan.load(args.plan)
    print(f"plan          : {plan.source}")
    print(f"count element : {plan.count_element.strategy}={plan.count_element.value}")
    print(f"filters       : {len(plan.filters)}")
    for name, fp in plan.filters.items():
        bits = []
        if fp.open:
            bits.append("open")
        if fp.apply:
            bits.append("apply")
        if fp.reset:
            bits.append("reset")
        print(f"  {name:<22} {len(fp.options)} options  [{', '.join(bits) or 'no controls'}]")
        if not fp.apply:
            print(f"      note: no apply locator — P2/P3 will assume live apply for {name}")
    print("\nPlan is structurally valid. It has NOT been checked against a live screen: "
          "every locator here is still a hypothesis until a probe run resolves it.")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    plan = ProbePlan.load(args.plan)
    try:
        from appium import webdriver
        from appium.options.android import UiAutomator2Options
    except ImportError as exc:
        raise RuntimeError("Appium-Python-Client is required for `run`. Use `infer` and "
                           "`selftest` to verify the logic without a device.") from exc
    import os
    opts = UiAutomator2Options()
    opts.platform_name = "Android"
    opts.automation_name = "UiAutomator2"
    opts.app_package = args.package
    if args.activity:
        opts.app_activity = args.activity
    if args.serial:
        opts.udid = args.serial
    opts.no_reset = True  # probing needs the session and search state the crawl left behind
    driver = webdriver.Remote(os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723"),
                              options=opts)
    policy = SafetyPolicy.load(args.safety_config, app_package=args.package,
                               permissive=False, environment=args.environment)
    prober = Prober(plan, policy, driver, max_actions=args.max_actions)
    requested = [p.strip().upper() for p in args.probes.split(",") if p.strip()]
    try:
        for fp in plan.filters.values():
            if "P1" in requested:
                prober.results.append(prober.p1_cardinality(fp))
            if "P2" in requested:
                prober.results.append(prober.p2_apply_mode(fp))
            if "P3" in requested:
                prober.results.append(prober.p3_and_or(fp))
        if "P5" in requested and args.expected_filters:
            prober.results.append(
                prober.p5_filter_existence([f.strip() for f in args.expected_filters.split(",")]))
    finally:
        meta = {"started": _now(), "app": args.package, "locale": args.locale,
                "plan": plan.source, "actions": prober.actions}
        out = write_filter_behaviour(prober.results, prober.refused, Path(args.out), meta)
        try:
            driver.quit()
        except Exception:  # pragma: no cover
            pass
        print(f"\nprobes run   : {len(prober.results)}")
        print(f"actions used : {prober.actions}/{prober.max_actions}")
        print(f"refused taps : {len(prober.refused)}")
        print(f"wrote        : {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="prober.py",
        description="PROBE mode: determine filter behaviour by experiment. The result count "
                    "is the instrument; raw counts are always recorded alongside verdicts.",
    )
    p.add_argument("--safety-config", default=None)
    p.add_argument("--environment", choices=["production", "staging"],
                   default=os.environ.get("TEST_ENVIRONMENT", "production"),
                   help="PRODUCTION by default; adds the data-creation blocklist")
    sub = p.add_subparsers(dest="command", required=True)

    st = sub.add_parser("selftest", help="verify the inference math with no device")
    st.set_defaults(func=lambda a: run_selftest())

    inf = sub.add_parser("infer", help="run one inference against numbers you supply")
    isub = inf.add_subparsers(dest="probe", required=True)

    c = isub.add_parser("cardinality", help="P1")
    c.add_argument("--a-still-selected", action="store_true")
    c.add_argument("--count-changed", action="store_true")
    c.add_argument("--not-live", action="store_true", help="filters are not applied live")
    c.set_defaults(func=_cmd_infer, probe="cardinality")

    am = isub.add_parser("apply-mode", help="P2")
    am.add_argument("--count-changed", action="store_true")
    am.add_argument("--label-changed", action="store_true")
    am.set_defaults(func=_cmd_infer, probe="apply-mode")

    ao = isub.add_parser("and-or", help="P3")
    ao.add_argument("--count-a", type=int, required=True)
    ao.add_argument("--count-b", type=int, required=True)
    ao.add_argument("--count-ab", type=int, required=True)
    ao.set_defaults(func=_cmd_infer, probe="and-or")

    co = isub.add_parser("constraint", help="P4")
    co.add_argument("--selectable", action="store_true")
    co.add_argument("--count", type=int, default=None)
    co.set_defaults(func=_cmd_infer, probe="constraint")

    bo = isub.add_parser("boundary", help="P6")
    bo.add_argument("--boundary", type=float, required=True)
    bo.add_argument("--returned", action="store_true", help="item at the boundary was returned")
    bo.add_argument("--count-at", type=int, default=None)
    bo.add_argument("--count-below", type=int, default=None)
    bo.set_defaults(func=_cmd_infer, probe="boundary")

    vp = sub.add_parser("validate-plan", help="structurally check a probe plan YAML")
    vp.add_argument("--plan", required=True)
    vp.set_defaults(func=_cmd_validate_plan)

    rn = sub.add_parser("run", help="execute probes against a live device")
    rn.add_argument("--plan", required=True)
    rn.add_argument("--probes", default="P1,P2,P3")
    rn.add_argument("--package", required=True)
    rn.add_argument("--activity", default=None)
    rn.add_argument("--serial", default=None)
    rn.add_argument("--locale", default="en-AE")
    rn.add_argument("--out", default="context/filter-behaviour.md")
    rn.add_argument("--max-actions", type=int, default=PROBE_ACTION_CAP)
    rn.add_argument("--expected-filters", default=None,
                    help="comma-separated filter names from filter-inventory.md, for P5")
    rn.set_defaults(func=_cmd_run)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
