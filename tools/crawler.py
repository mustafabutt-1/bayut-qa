"""PASSIVE crawler: traverse the live Bayut app and inventory what is actually there.

Every tap passes through ``crawl_safety.SafetyPolicy`` first. Every tap is preceded by
a screenshot. The crawl stops hard at the action cap. These three properties are not
configurable away.

Two execution modes:

  live     drives a real device over Appium
  offline  replays a directory of page-source XML files, so the fingerprinting,
           safety classification and report generation can be verified with no
           device attached

CLI
---
    python tools/crawler.py plan     --page-source dump.xml
    python tools/crawler.py offline  --fixtures-dir tests/fixtures/page_source --out context
    python tools/crawler.py crawl    --package com.bayut.app --locale en-AE --out context
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adb import Adb, AdbError
from crawl_safety import SafetyDecision, SafetyPolicy
from pagesource import Element, parse_page_source, screen_fingerprint, tappable

# --- hard limits: see .claude/agents/app-cartographer.md, SAFETY -------------
ACTION_CAP = 400
MIN_ACTION_INTERVAL_S = 0.8
DEFAULT_DEPTH = 4
PINNING_VERDICT_AFTER_S = 300  # report cert pinning within 5 minutes, not at the end


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass
class ScreenRecord:
    fingerprint: str            # structural: resource-ids only, locale-invariant
    name: str
    first_seen_via: str
    locale: str
    element_count: int = 0
    tappable_count: int = 0
    stability_counts: dict[str, int] = field(default_factory=dict)
    page_source_path: str = ""
    screenshot_path: str = ""
    elements: list[dict[str, Any]] = field(default_factory=list)
    # Every user-visible string on the screen, including non-clickable, unidentified
    # TextViews. Kept separately because `elements` is filtered for the locator
    # inventory, and the listing ID most often sits on exactly the elements that filter
    # drops ("Reference no. 7419283").
    visible_strings: list[dict[str, str]] = field(default_factory=list)
    # Includes localized content-desc. Differs from `fingerprint` exactly when the
    # screen carries accessibility labels; comparing it across locales is how
    # content-desc localization gaps become visible.
    full_fingerprint: str = ""
    visits: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "full_fingerprint": self.full_fingerprint,
            "name": self.name,
            "first_seen_via": self.first_seen_via,
            "locale": self.locale,
            "element_count": self.element_count,
            "tappable_count": self.tappable_count,
            "stability": self.stability_counts,
            "page_source": self.page_source_path,
            "screenshot": self.screenshot_path,
            "visits": self.visits,
        }


@dataclass
class Edge:
    src: str
    dst: str
    via_label: str
    via_locator: str


@dataclass
class CrawlModel:
    """Everything the crawl learned. Report writers read only this."""

    screens: dict[str, ScreenRecord] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    blocked: list[dict[str, Any]] = field(default_factory=list)
    uncertain: list[dict[str, Any]] = field(default_factory=list)
    dead_ends: list[dict[str, Any]] = field(default_factory=list)
    actions_used: int = 0
    stopped_reason: str = "completed"
    meta: dict[str, Any] = field(default_factory=dict)

    def add_screen(self, rec: ScreenRecord) -> bool:
        """Returns True when the screen is new."""
        if rec.fingerprint in self.screens:
            self.screens[rec.fingerprint].visits += 1
            return False
        self.screens[rec.fingerprint] = rec
        return True


# ---------------------------------------------------------------------------
# Certificate-pinning watchdog
# ---------------------------------------------------------------------------


class PinningWatchdog:
    """Answers one question early: is mitmproxy seeing any traffic at all?

    If the proxy is configured and the flow file never grows, certificate pinning is
    the most likely explanation — and that kills the API-oracle strategy, so it must
    surface in the first minutes of the first crawl, not in the final report.
    """

    def __init__(self, flow_file: Path | None, out_dir: Path,
                 verdict_after_s: int = PINNING_VERDICT_AFTER_S) -> None:
        self.flow_file = flow_file
        self.out_dir = out_dir
        self.verdict_after_s = verdict_after_s
        self.verdict: str = "NOT_STARTED"
        self.detail: str = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = 0.0

    def start(self) -> None:
        self._started_at = time.time()
        if self.flow_file is None:
            self.verdict = "MITM_NOT_CONFIGURED"
            self.detail = ("No --mitm-flow-file given. The crawl will produce no API "
                           "evidence and cert pinning stays UNRESOLVED.")
            print(f"\n!! {self.verdict}: {self.detail}\n", file=sys.stderr)
            self._write()
            return
        self.verdict = "WATCHING"
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _size(self) -> int:
        try:
            return self.flow_file.stat().st_size if self.flow_file else 0
        except OSError:
            return 0

    def _loop(self) -> None:
        baseline = self._size()
        while not self._stop.wait(15):
            elapsed = time.time() - self._started_at
            if self._size() > baseline:
                self.verdict = "TRAFFIC_SEEN"
                self.detail = (f"Proxy captured traffic within {int(elapsed)}s. "
                               f"Interception works; the API oracle is viable.")
                print(f"\n== {self.verdict}: {self.detail}\n", file=sys.stderr)
                self._write()
                return
            if elapsed >= self.verdict_after_s:
                self.verdict = "PINNING_SUSPECTED"
                self.detail = (
                    f"Zero proxy traffic after {int(elapsed)}s of active crawling with the "
                    f"device proxy set. Certificate pinning is the most likely cause."
                )
                print("\n" + "!" * 78, file=sys.stderr)
                print(f"!! {self.verdict}", file=sys.stderr)
                print(f"!! {self.detail}", file=sys.stderr)
                print("!! Confirm now, do not wait for the crawl to finish:", file=sys.stderr)
                print("!!   1. Does the app still load listings with the proxy on?", file=sys.stderr)
                print("!!      loads = pinning bypassed for this host, or traffic is not HTTP", file=sys.stderr)
                print("!!      fails = pinning is on", file=sys.stderr)
                print("!!   2. Check the mitmproxy console for TLS handshake errors.", file=sys.stderr)
                print("!! If pinning is on, oracle.py and har_diff.py are blocked until dev "
                      "ships a debug build that trusts user CAs.", file=sys.stderr)
                print("!" * 78 + "\n", file=sys.stderr)
                self._write()
                return

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self.verdict == "WATCHING":
            self.verdict = "INCONCLUSIVE"
            self.detail = "Crawl ended before the watchdog reached a verdict."
        self._write()

    def _write(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "pinning-check.md").write_text(
            "# Certificate Pinning Check\n\n"
            f"- **Verdict:** {self.verdict}\n"
            f"- **Checked:** {_now()}\n"
            f"- **Flow file:** {self.flow_file or '(none configured)'}\n\n"
            f"{self.detail}\n\n"
            "## Why this matters\n\n"
            "If the app pins certificates, mitmproxy sees nothing, and the API oracle "
            "(`oracle.py`) and contract diffing (`har_diff.py`) cannot be built. That is "
            "the most differentiated part of this QA design, so a PINNING_SUSPECTED "
            "verdict is a programme-level blocker, not a tooling inconvenience. The ask "
            "to dev is a debug build with a network security config that trusts user CAs.\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------


@dataclass
class CrawlConfig:
    package: str
    activity: str | None = None
    serial: str | None = None
    locale: str = "en-AE"
    out_dir: Path = Path("context")
    artifacts_dir: Path = Path("runs/crawl")
    max_actions: int = ACTION_CAP
    max_depth: int = DEFAULT_DEPTH
    action_interval: float = MIN_ACTION_INTERVAL_S
    permissive: bool = False
    safety_config: str | None = None
    environment: str = "production"
    mitm_flow_file: Path | None = None
    settle_seconds: float = 2.0
    preserve_app_state: bool = False
    bootstrap_path: list[dict[str, str]] = field(default_factory=list)


class Crawler:
    def __init__(self, cfg: CrawlConfig) -> None:
        if cfg.max_actions > ACTION_CAP:
            raise ValueError(f"max_actions cannot exceed the hard cap of {ACTION_CAP}")
        if cfg.action_interval < MIN_ACTION_INTERVAL_S:
            raise ValueError(f"action_interval cannot go below {MIN_ACTION_INTERVAL_S}s "
                             f"(bot-detection guard)")
        self.cfg = cfg
        self.policy = SafetyPolicy.load(cfg.safety_config, app_package=cfg.package,
                                        permissive=cfg.permissive,
                                        environment=cfg.environment)  # type: ignore[arg-type]
        self.model = CrawlModel()
        self.adb = Adb(cfg.serial)
        self.driver: Any = None
        self.watchdog = PinningWatchdog(cfg.mitm_flow_file, cfg.out_dir)

    # -- driver ----------------------------------------------------------

    def _start_driver(self) -> None:
        try:
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
        except ImportError as exc:
            raise RuntimeError(
                "Appium-Python-Client is not installed. `pip install -r requirements.txt`, "
                "or use `crawler.py offline` to work against fixture page sources."
            ) from exc
        opts = UiAutomator2Options()
        opts.platform_name = "Android"
        opts.automation_name = "UiAutomator2"
        opts.app_package = self.cfg.package
        if self.cfg.activity:
            opts.app_activity = self.cfg.activity
        if self.cfg.serial:
            opts.udid = self.cfg.serial
        # False (default) wipes app data at session start — the correct behaviour for a
        # genuine first-ever crawl. True skips the wipe, so a crawl can resume against
        # app state left by a prior onboarding walkthrough or an earlier crawl segment,
        # instead of re-facing a one-time onboarding flow it cannot get past on its own.
        opts.no_reset = self.cfg.preserve_app_state
        opts.new_command_timeout = int(os.environ.get("APPIUM_NEW_COMMAND_TIMEOUT", "120"))
        opts.auto_grant_permissions = False  # never silently grant; permissions are a test surface
        server = os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
        self.driver = webdriver.Remote(server, options=opts)

    # -- primitives ------------------------------------------------------

    def _budget_left(self) -> int:
        return self.cfg.max_actions - self.model.actions_used

    def _spend_action(self) -> None:
        self.model.actions_used += 1
        time.sleep(self.cfg.action_interval)

    def _capture(self, tag: str) -> tuple[list[Element], str, Path]:
        """Page source + fingerprint + screenshot for the current screen."""
        xml = self.driver.page_source
        elements = parse_page_source(xml)
        fp = screen_fingerprint(elements)
        ps_dir = self.cfg.out_dir / "page_source"
        ps_dir.mkdir(parents=True, exist_ok=True)
        ps_path = ps_dir / f"{self.cfg.locale}-{fp}.xml"
        if not ps_path.exists():
            ps_path.write_text(xml, encoding="utf-8")
        shot_dir = self.cfg.artifacts_dir / "screenshots"
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot = shot_dir / f"{tag}-{fp}.png"
        try:
            self.driver.get_screenshot_as_file(str(shot))
        except Exception as exc:  # pragma: no cover - device dependent
            print(f"  warning: screenshot failed ({exc}); tapping anyway is NOT permitted",
                  file=sys.stderr)
            raise
        return elements, fp, ps_path

    def _record_screen(self, elements: list[Element], fp: str, via: str,
                       ps_path: Path) -> ScreenRecord:
        taps = tappable(elements)
        stability: dict[str, int] = {}
        for el in elements:
            stability[el.stability] = stability.get(el.stability, 0) + 1
        rec = ScreenRecord(
            fingerprint=fp,
            name=_guess_screen_name(elements),
            first_seen_via=via,
            locale=self.cfg.locale,
            element_count=len(elements),
            tappable_count=len(taps),
            stability_counts=stability,
            page_source_path=str(ps_path),
            elements=[el.to_dict() for el in elements if el.stable_identifier or el.clickable],
            visible_strings=_visible_strings(elements),
            full_fingerprint=screen_fingerprint(elements, mode="full"),
        )
        self.model.add_screen(rec)
        return self.model.screens[fp]

    def _tap(self, el: Element) -> bool:
        """The only place a tap happens. Safety gate is not bypassable."""
        allowed, decision = self.policy.may_tap(el)
        entry = {**decision.to_dict(), "at": _now()}
        if decision.verdict == "BLOCK":
            self.model.blocked.append(entry)
            return False
        if decision.verdict == "UNCERTAIN":
            self.model.uncertain.append(entry)
            if not allowed:
                return False
        point = el.center
        if point is None:
            return False
        self.driver.tap([point], 100)
        self._spend_action()
        time.sleep(self.cfg.settle_seconds)
        return True

    def _back(self) -> None:
        self.driver.back()
        self._spend_action()
        time.sleep(self.cfg.settle_seconds)

    def _reset_to_home(self) -> None:
        """Force-stop + relaunch — deliberately *not* `pm clear`.

        Bayut's onboarding (region/purpose questions, tracking-permission prompt) is
        one-time-only, gated on app data, not on process state. `pm clear` here would
        wipe that flag on every dead-end recovery and every queued-path replay, so the
        crawl would face onboarding again on its very next reset and could never reach
        anything past it. A clean process restart still guarantees known state (no
        stale UI, no leftover dialogs) without re-triggering first-run flows.
        """
        self.adb.stop_app(self.cfg.package)
        self.adb.launch_app(self.cfg.package, self.cfg.activity)
        time.sleep(self.cfg.settle_seconds * 2)
        # A cold relaunch lands on the app's own default screen (its default tab),
        # which is not necessarily where this crawl actually started — e.g. when
        # --preserve-app-state was bootstrapped into a specific section by hand
        # before the crawl began. Replay that bootstrap here so every reset returns
        # to the crawl's real starting point, not the app's.
        for step in self.cfg.bootstrap_path:
            elements, _, _ = self._capture("bootstrap")
            target = _find_step(elements, step)
            if target is None:
                break
            if not self._tap(target):
                break

    # -- traversal -------------------------------------------------------

    def crawl(self) -> CrawlModel:
        self.watchdog.start()
        started = time.time()
        try:
            self._start_driver()
            self.model.meta = {
                "started": _now(),
                "package": self.cfg.package,
                "locale": self.cfg.locale,
                "mode": "PERMISSIVE" if self.cfg.permissive else "STRICT",
                "environment": self.cfg.environment,
                "max_actions": self.cfg.max_actions,
                "max_depth": self.cfg.max_depth,
            }
            try:
                self.model.meta["app"] = self.adb.app_version(self.cfg.package)
            except AdbError as exc:
                self.model.meta["app"] = {"error": str(exc)}

            elements, fp, ps = self._capture("home")
            self._record_screen(elements, fp, "app launch", ps)
            queue: deque[tuple[list[dict[str, str]], str]] = deque()
            queue.append(([], fp))

            while queue and self._budget_left() > 0:
                path, origin_fp = queue.popleft()
                if len(path) >= self.cfg.max_depth:
                    continue
                if not self._navigate(path):
                    self.model.dead_ends.append(
                        {"path": path, "reason": "replay failed", "at": _now()})
                    continue
                elements, fp, ps = self._capture(f"d{len(path)}")
                origin = self._record_screen(elements, fp, _describe(path), ps)

                # `stop_crawl` distinguishes the two reasons for leaving this screen's
                # element loop: an exhausted action budget ends the whole crawl, while a
                # dead end only abandons this screen and moves on to the next queued
                # path. A for/else/break would have conflated them and ended the entire
                # crawl at the first back-navigation failure.
                stop_crawl = False
                for el in tappable(elements):
                    if self._budget_left() <= 0:
                        self.model.stopped_reason = f"action cap reached ({self.cfg.max_actions})"
                        stop_crawl = True
                        break
                    step = {"strategy": el.locator_strategy, "value": el.locator_value,
                            "label": el.label}
                    if not self._tap(el):
                        continue
                    new_elements, new_fp, new_ps = self._capture(f"d{len(path) + 1}")
                    if new_elements and not any(e.package == self.cfg.package for e in new_elements):
                        # The tap (or something racing it, e.g. a heads-up notification
                        # from an unrelated app intercepting the tap coordinates) left
                        # the app under test entirely. Never record a foreign screen as
                        # part of this app's map — every element on it would also be
                        # BLOCK-FOREIGN-PACKAGE if we tried to tap further anyway, but
                        # recording the screen itself would silently corrupt the graph.
                        self.model.dead_ends.append({
                            "from": origin.fingerprint, "via": el.label,
                            "landed_on": new_fp,
                            "reason": "tap left the app under test (foreign package); not recorded",
                            "at": _now()})
                        self._reset_to_home()
                        break
                    if new_fp != origin.fingerprint:
                        is_new = self.model.add_screen(
                            self._record_screen(new_elements, new_fp, _describe(path + [step]), new_ps)
                        )
                        self.model.edges.append(
                            Edge(origin.fingerprint, new_fp, el.label, f"{el.locator_strategy}={el.locator_value}"))
                        if is_new:
                            queue.append((path + [step], new_fp))
                        self._back()
                        back_elements, back_fp, _ = self._capture("back")
                        if back_fp == new_fp and back_fp != origin.fingerprint:
                            # Back had no visible effect at all — commonly a screen
                            # that auto-focused a text field, so the first back only
                            # dismissed the IME keyboard rather than navigating. One
                            # more back before treating this as a genuine dead end.
                            self._back()
                            back_elements, back_fp, _ = self._capture("back")
                        if back_fp != origin.fingerprint:
                            self.model.dead_ends.append({
                                "from": origin.fingerprint, "via": el.label,
                                "landed_on": back_fp,
                                "reason": "back did not return to origin; resetting",
                                "at": _now()})
                            self._reset_to_home()
                            break
                if stop_crawl:
                    break

            if self._budget_left() <= 0:
                self.model.stopped_reason = f"action cap reached ({self.cfg.max_actions})"
        finally:
            self.watchdog.stop()
            self.model.meta["finished"] = _now()
            self.model.meta["duration_s"] = round(time.time() - started, 1)
            self.model.meta["pinning_verdict"] = self.watchdog.verdict
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:  # pragma: no cover
                    pass
        return self.model

    def _navigate(self, path: list[dict[str, str]]) -> bool:
        """Replay a path from a freshly reset app. Costs actions, guarantees state.

        The empty path (the root queue item) is the crawl's own starting screen —
        already captured once, right before the queue was seeded. Resetting for it
        too would discard that starting position for no replay benefit: with
        --preserve-app-state the reset lands wherever the app defaults to on a cold
        relaunch (its default tab), which is not necessarily the screen the crawl
        actually started from, so every subsequent step in the (empty) path would
        have nothing to replay against.
        """
        if path:
            self._reset_to_home()
        for step in path:
            if self._budget_left() <= 0:
                return False
            elements, _, _ = self._capture("replay")
            target = _find_step(elements, step)
            if target is None:
                return False
            if not self._tap(target):
                return False
        return True


def _find_step(elements: list[Element], step: dict[str, str]) -> Element | None:
    for el in elements:
        if el.locator_strategy == step["strategy"] and el.locator_value == step["value"]:
            return el
    for el in elements:  # fall back to label, since text can shift with content
        if el.label == step.get("label"):
            return el
    return None


def _visible_strings(elements: list[Element]) -> list[dict[str, str]]:
    """Text and content-desc of every element, identified or not."""
    return [
        {"text": el.text, "content_desc": el.content_desc, "class": el.klass}
        for el in elements
        if el.text or el.content_desc
    ]


def _describe(path: list[dict[str, str]]) -> str:
    return " → ".join(["launch"] + [s["label"] for s in path]) if path else "app launch"


_NAME_HINTS = (
    ("search_results", r"(result|listing_card|property_card|srp)"),
    ("listing_detail", r"(ldp|listing_detail|property_detail|amenit)"),
    ("filters", r"(filter|refine|sort_)"),
    ("home", r"(home|discover|explore)"),
    ("favourites", r"(favou?rite|saved|shortlist)"),
    ("login", r"(login|sign_?in|otp|password)"),
    ("profile", r"(profile|settings|account)"),
    ("map", r"(map|marker|cluster)"),
)


def _guess_screen_name(elements: list[Element]) -> str:
    """A hint only. app-cartographer renames screens from evidence; never trust this."""
    blob = " ".join(f"{el.resource_id} {el.content_desc}" for el in elements).lower()
    for name, pattern in _NAME_HINTS:
        if re.search(pattern, blob):
            return f"{name} [UNRESOLVED — name inferred from identifiers]"
    return "UNRESOLVED — unnamed screen"


# ---------------------------------------------------------------------------
# Report writers — the only consumers of CrawlModel
# ---------------------------------------------------------------------------


def write_reports(model: CrawlModel, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = [
        _write_screen_inventory(model, out_dir / "screen-inventory.observed.md"),
        _write_element_inventory(model, out_dir / "element-inventory.json"),
        _write_screen_graph(model, out_dir / "screen-graph.mermaid"),
        _write_locator_quality(model, out_dir / "locator-quality.md"),
        _write_blocked(model, out_dir / "crawl-blocked.md"),
        _write_uncertain(model, out_dir / "crawl-uncertain.md"),
        _write_listing_id_visibility(model, out_dir / "listing-id-visibility.md"),
    ]
    return written


def _header(model: CrawlModel, title: str) -> str:
    m = model.meta
    app = m.get("app", {}) if isinstance(m.get("app"), dict) else {}
    return (
        f"# {title}\n\n"
        f"Generated by `tools/crawler.py` — **OBSERVED**, not inferred.\n\n"
        f"- Crawled: {m.get('started', 'UNKNOWN')} → {m.get('finished', 'UNKNOWN')}\n"
        f"- App: {app.get('package', 'UNKNOWN')} "
        f"v{app.get('version_name', 'UNKNOWN')} ({app.get('version_code', 'UNKNOWN')})\n"
        f"- Locale: {m.get('locale', 'UNKNOWN')}\n"
        f"- Environment: {str(m.get('environment', 'UNKNOWN')).upper()}\n"
        f"- Safety mode: {m.get('mode', 'UNKNOWN')}\n"
        f"- Actions used: {model.actions_used} / {m.get('max_actions', ACTION_CAP)}\n"
        f"- Stopped because: {model.stopped_reason}\n"
        f"- Pinning verdict: {m.get('pinning_verdict', 'UNKNOWN')}\n\n"
    )


def _write_screen_inventory(model: CrawlModel, path: Path) -> Path:
    lines = [_header(model, "Screen Inventory — Observed")]
    lines.append(f"{len(model.screens)} distinct screens reached.\n")
    for rec in model.screens.values():
        s = rec.stability_counts
        no_labels = (" — identical to the structural fingerprint, meaning no element on "
                     "this screen carries a content-desc. Nothing here is reachable by "
                     "TalkBack, and every locator falls back to resource-id or worse.")
        localized_note = no_labels if rec.full_fingerprint == rec.fingerprint else ""
        lines.append(
            f"### {rec.name}\n"
            f"Fingerprint: `{rec.fingerprint}` (structural, locale-invariant)\n\n"
            f"- Reached via: {rec.first_seen_via}\n"
            f"- Locale observed: {rec.locale}\n"
            f"- Elements: {rec.element_count} "
            f"(HIGH {s.get('HIGH', 0)} accessibility id, MEDIUM {s.get('MEDIUM', 0)} resource-id, "
            f"LOW {s.get('LOW', 0)} text-only, FRAGILE {s.get('FRAGILE', 0)} no identifier)\n"
            f"- Tappable: {rec.tappable_count}\n"
            f"- Page source: `{rec.page_source_path}`\n"
            f"- Deep link: UNRESOLVED — not tested by a passive crawl\n"
            f"- Localized fingerprint: `{rec.full_fingerprint}`{localized_note}\n"
            f"- Locale variance: UNRESOLVED — crawl the other locale, then "
            f"`pagesource.py diff --mode structural` the two dumps\n"
        )
    if model.dead_ends:
        lines.append("\n## Dead ends\n")
        for d in model.dead_ends:
            lines.append(f"- {d.get('reason')} — {json.dumps(d, ensure_ascii=False)}\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_element_inventory(model: CrawlModel, path: Path) -> Path:
    payload = {
        "meta": model.meta,
        "screens": {
            rec.fingerprint: {
                "name": rec.name,
                "locale": rec.locale,
                "page_source": rec.page_source_path,
                "elements": rec.elements,
            }
            for rec in model.screens.values()
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _write_screen_graph(model: CrawlModel, path: Path) -> Path:
    lines = ["```mermaid", "graph TD"]
    for rec in model.screens.values():
        label = rec.name.split(" [")[0]
        lines.append(f'    {rec.fingerprint}["{label}<br/><small>{rec.fingerprint}</small>"]')
    for e in model.edges:
        safe = e.via_label.replace('"', "'")[:28] or "(unlabelled)"
        lines.append(f'    {e.src} -->|"{safe}"| {e.dst}')
    lines.append("```")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_locator_quality(model: CrawlModel, path: Path) -> Path:
    lines = [_header(model, "Locator Quality — the testID ask, itemised")]
    lines.append(
        "Every element below has no stable identifier, or only a text label that breaks "
        "under Arabic. The `Suggested accessibility id` column exists so this reads as a "
        "one-line change for dev rather than a complaint from QA.\n\n"
        "Frame this as accessibility compliance: an element with no `contentDescription` "
        "is also unreachable by TalkBack.\n"
    )
    total = 0
    for rec in model.screens.values():
        weak = [e for e in rec.elements if e.get("stability") in ("LOW", "FRAGILE")
                and (e.get("clickable") or e.get("label"))]
        if not weak:
            continue
        total += len(weak)
        lines.append(f"\n## {rec.name} — {len(weak)}\n")
        lines.append("| Element | Current best locator | Stability | Suggested accessibility id |")
        lines.append("|---|---|---|---|")
        for e in weak:
            label = str(e.get("label", ""))[:36]
            loc = f"{e.get('locator_strategy')}={str(e.get('locator_value'))[:44]}"
            lines.append(f"| {label} | `{loc}` | {e.get('stability')} | `{_suggest_id(rec.name, label)}` |")
    lines.insert(1, f"\n**{total} elements need an identifier.**\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _suggest_id(screen_name: str, label: str) -> str:
    screen = re.sub(r"[^a-z0-9]+", "_", screen_name.split(" [")[0].lower()).strip("_")
    el = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "element"
    return f"{screen}_{el}"[:56]


def _write_blocked(model: CrawlModel, path: Path) -> Path:
    lines = [_header(model, "Blocked Taps — consequential actions in the app")]
    lines.append(
        f"{len(model.blocked)} tap(s) were refused by `tools/crawl_safety.py`. This list is "
        "itself a finding: it enumerates every control in the app that has a real-world "
        "consequence, which is exactly the set a human tester must handle manually.\n"
    )
    if not model.blocked:
        lines.append("\n_No blocked taps recorded._\n")
    else:
        lines.append("\n| Element | Rule | Category | Reason |")
        lines.append("|---|---|---|---|")
        for b in model.blocked:
            lines.append(f"| {str(b.get('element'))[:36]} | `{b.get('rule_id')}` | "
                         f"{b.get('category')} | {str(b.get('reason'))[:88]} |")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_uncertain(model: CrawlModel, path: Path) -> Path:
    lines = [_header(model, "Uncertain Taps — needs human review")]
    lines.append(
        f"{len(model.uncertain)} element(s) matched no allow rule and no block rule. In STRICT "
        "mode they were **not** tapped, so any screen behind them is unmapped.\n\n"
        "**Review these, then promote the safe ones** by adding allow rules to "
        "`context/crawl-allowlist.yaml`; the next crawl will reach further. Leave anything "
        "consequential alone and add it to the blocklist instead.\n"
    )
    if not model.uncertain:
        lines.append("\n_No uncertain elements recorded._\n")
    else:
        lines.append("\n| Element | Locator | Suggested action |")
        lines.append("|---|---|---|")
        seen = set()
        for u in model.uncertain:
            key = (u.get("element"), u.get("locator"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"| {str(u.get('element'))[:36]} | `{str(u.get('locator'))[:52]}` | "
                         f"allow / block / leave |")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# Candidate listing-ID shapes seen in property portals. Reported, never assumed.
# Only user-visible surfaces are scanned: a resource-id is a compile-time name and can
# never carry a listing identifier, so including it would manufacture false candidates
# and push the verdict to CANDIDATES FOUND when nothing usable is on screen.
_ID_SURFACES = ("text", "content_desc")
_ID_PATTERNS = (
    ("numeric_6_9", re.compile(r"(?<!\d)\d{6,9}(?!\d)")),
    ("prefixed", re.compile(
        r"\b(?:id|listing|propert(?:y|ies)|ref(?:erence)?)\s*(?:no\.?|number|#|:)?\s*"
        r"([A-Za-z]{0,3}\d{4,})\b", re.I)),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
)


def _write_listing_id_visibility(model: CrawlModel, path: Path) -> Path:
    findings: list[tuple[str, str, str, str]] = []
    for rec in model.screens.values():
        for e in rec.visible_strings:
            for surface in _ID_SURFACES:
                value = str(e.get(surface) or "")
                if not value:
                    continue
                for name, pattern in _ID_PATTERNS:
                    if pattern.search(value):
                        findings.append((rec.name, surface, name, value[:70]))
                        break

    if findings:
        verdict = "CANDIDATES FOUND — needs human confirmation"
        consequence = (
            "Candidate identifiers are visible in the UI. A human must confirm that one of "
            "them is the same identifier the search API returns for that listing. If it is, "
            "`oracle.py` can do exact set matching, which is the strong form of the check."
        )
    else:
        verdict = "NO CANDIDATES FOUND"
        consequence = (
            "No listing-ID-shaped value was found on any crawled surface. Unless one appears "
            "in a share link or an untested screen, `oracle.py` must degrade to fuzzy "
            "matching on price + title + beds — which is weakest precisely where a dropped "
            "listing is most likely: near-identical units in the same tower. **Making the "
            "listing ID available as a `contentDescription` is then a top-3 ask to dev.**"
        )

    lines = [_header(model, "Listing ID Visibility — can the oracle match exactly?")]
    lines.append(f"## Verdict: {verdict}\n\n{consequence}\n")
    lines.append("\n## Surfaces checked\n\nEvery user-visible string on every crawled screen: "
                 "`text` and `content-desc`, including non-clickable and unidentified views. "
                 "`resource-id` is deliberately excluded — it is a compile-time name and can "
                 "never carry a listing identifier.\n\n**Not** checked by a passive crawl: the "
                 "outbound share-link URL (blocked — share opens the OS sheet) and the API "
                 "response (needs mitmproxy). Both remain UNRESOLVED here.\n")
    if findings:
        lines.append("\n| Screen | Surface | Pattern | Value |")
        lines.append("|---|---|---|---|")
        for screen, surface, pattern, value in findings[:60]:
            lines.append(f"| {screen[:28]} | {surface} | {pattern} | `{value}` |")
        if len(findings) > 60:
            lines.append(f"\n_+{len(findings) - 60} more._\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Offline mode — verify the whole pipeline with no device
# ---------------------------------------------------------------------------


def crawl_offline(fixtures_dir: Path, out_dir: Path, *, policy: SafetyPolicy,
                  locale: str = "en-AE") -> CrawlModel:
    """Treat each XML file in a directory as a visited screen.

    Exercises parsing, fingerprinting, safety classification and every report writer.
    It cannot exercise tapping, navigation or back-handling — those need a device.
    """
    files = sorted(fixtures_dir.glob("*.xml"))
    if not files:
        raise FileNotFoundError(f"no .xml page sources in {fixtures_dir}")
    model = CrawlModel()
    model.meta = {
        "started": _now(), "finished": _now(), "locale": locale,
        "mode": "OFFLINE (" + ("PERMISSIVE" if policy.permissive else "STRICT") + ")",
        "environment": policy.environment,
        "max_actions": 0, "pinning_verdict": "N/A — offline",
        "app": {"package": policy.app_package or "UNKNOWN", "version_name": "OFFLINE"},
    }
    previous_fp: str | None = None
    for f in files:
        elements = parse_page_source(f.read_text(encoding="utf-8", errors="replace"))
        fp = screen_fingerprint(elements)
        stability: dict[str, int] = {}
        for el in elements:
            stability[el.stability] = stability.get(el.stability, 0) + 1
        rec = ScreenRecord(
            fingerprint=fp, name=f"{f.stem} ({_guess_screen_name(elements)})",
            first_seen_via=f"fixture {f.name}", locale=locale,
            element_count=len(elements), tappable_count=len(tappable(elements)),
            stability_counts=stability, page_source_path=str(f),
            elements=[el.to_dict() for el in elements if el.stable_identifier or el.clickable],
            visible_strings=_visible_strings(elements),
            full_fingerprint=screen_fingerprint(elements, mode="full"),
        )
        model.add_screen(rec)
        for el in tappable(elements):
            d = policy.evaluate(el)
            entry = {**d.to_dict(), "at": _now()}
            if d.verdict == "BLOCK":
                model.blocked.append(entry)
            elif d.verdict == "UNCERTAIN":
                model.uncertain.append(entry)
        if previous_fp and previous_fp != fp:
            model.edges.append(Edge(previous_fp, fp, "(fixture order)", "offline"))
        previous_fp = fp
    model.stopped_reason = "offline replay completed"
    return model


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_plan(args: argparse.Namespace) -> int:
    """Show what a crawl would do on one screen, without touching the device."""
    policy = SafetyPolicy.load(args.safety_config, app_package=args.package,
                               permissive=args.allow_uncertain_taps,
                               environment=args.environment)
    elements = parse_page_source(Path(args.page_source).read_text(encoding="utf-8", errors="replace"))
    targets = tappable(elements)
    parts = policy.partition(targets)
    print(f"screen fingerprint : {screen_fingerprint(elements)}")
    print(f"name hint          : {_guess_screen_name(elements)}")
    print(f"elements           : {len(elements)}  tappable: {len(targets)}")
    print(f"mode               : {'PERMISSIVE' if policy.permissive else 'STRICT'}")
    print(f"would tap          : {len(parts['ALLOW']) + (len(parts['UNCERTAIN']) if policy.permissive else 0)}")
    print(f"would block        : {len(parts['BLOCK'])}")
    print(f"would skip         : {0 if policy.permissive else len(parts['UNCERTAIN'])} (uncertain)\n")
    for verdict in ("BLOCK", "ALLOW", "UNCERTAIN"):
        for d in parts[verdict]:
            print(f"  {verdict:<10} {d.element_label[:34]:<36} {d.rule_id or '-'}")
    return 0


def _cmd_offline(args: argparse.Namespace) -> int:
    policy = SafetyPolicy.load(args.safety_config, app_package=args.package,
                               permissive=args.allow_uncertain_taps,
                               environment=args.environment)
    model = crawl_offline(Path(args.fixtures_dir), Path(args.out), policy=policy, locale=args.locale)
    written = write_reports(model, Path(args.out))
    print(f"screens   : {len(model.screens)}")
    print(f"blocked   : {len(model.blocked)}")
    print(f"uncertain : {len(model.uncertain)}")
    print("\nwrote:")
    for p in written:
        print(f"  {p}")
    return 0


def _cmd_crawl(args: argparse.Namespace) -> int:
    cfg = CrawlConfig(
        package=args.package, activity=args.activity, serial=args.serial,
        locale=args.locale, out_dir=Path(args.out), artifacts_dir=Path(args.artifacts),
        max_actions=args.max_actions, max_depth=args.max_depth,
        permissive=args.allow_uncertain_taps, safety_config=args.safety_config,
        environment=args.environment,
        mitm_flow_file=Path(args.mitm_flow_file) if args.mitm_flow_file else None,
        preserve_app_state=args.preserve_app_state,
        bootstrap_path=(
            [{"strategy": "accessibility id", "value": args.bootstrap_content_desc,
              "label": args.bootstrap_content_desc}]
            if args.bootstrap_content_desc else []
        ),
    )
    if cfg.permissive:
        print("\n" + "!" * 78)
        print("!! PERMISSIVE MODE: elements matching no allow rule WILL be tapped.")
        print("!! The blocklist still applies, but it cannot know about a control it has")
        print("!! never seen. Only run this supervised, on a staging build if one exists.")
        print("!" * 78 + "\n")
    crawler = Crawler(cfg)
    model = crawler.crawl()
    written = write_reports(model, cfg.out_dir)
    print(f"\nactions used : {model.actions_used}/{cfg.max_actions}")
    print(f"screens      : {len(model.screens)}")
    print(f"blocked taps : {len(model.blocked)}")
    print(f"uncertain    : {len(model.uncertain)}")
    print(f"stopped      : {model.stopped_reason}")
    print(f"pinning      : {crawler.watchdog.verdict}")
    print("\nwrote:")
    for p in written:
        print(f"  {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="crawler.py",
        description="PASSIVE app crawler. Every tap is safety-gated and screenshotted; "
                    f"the crawl stops hard at {ACTION_CAP} actions.",
    )
    p.add_argument("--safety-config", default=None, help="YAML allow/block extensions")
    p.add_argument("--environment", choices=["production", "staging"],
                   default=os.environ.get("TEST_ENVIRONMENT", "production"),
                   help="PRODUCTION by default and until told otherwise; adds the "
                        "data-creation blocklist")
    p.add_argument("--allow-uncertain-taps", action="store_true",
                   help="PERMISSIVE mode: tap elements that match no allow rule (supervised only)")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("plan", help="dry-run the tap decisions for one page-source dump")
    pl.add_argument("--page-source", required=True)
    pl.add_argument("--package", default=os.environ.get("BAYUT_APP_PACKAGE"))
    pl.set_defaults(func=_cmd_plan)

    off = sub.add_parser("offline", help="build all reports from a directory of page sources")
    off.add_argument("--fixtures-dir", required=True)
    off.add_argument("--out", default="context")
    off.add_argument("--locale", default="en-AE")
    off.add_argument("--package", default=os.environ.get("BAYUT_APP_PACKAGE", "com.bayut.app"))
    off.set_defaults(func=_cmd_offline)

    cr = sub.add_parser("crawl", help="crawl a live device over Appium")
    cr.add_argument("--package", default=os.environ.get("BAYUT_APP_PACKAGE"), required=False)
    cr.add_argument("--activity", default=os.environ.get("BAYUT_APP_ACTIVITY"))
    cr.add_argument("--serial", default=None)
    cr.add_argument("--locale", default="en-AE")
    cr.add_argument("--out", default="context")
    cr.add_argument("--artifacts", default="runs/crawl")
    cr.add_argument("--max-actions", type=int, default=ACTION_CAP,
                    help=f"hard cap is {ACTION_CAP}; lower values are allowed")
    cr.add_argument("--max-depth", type=int, default=DEFAULT_DEPTH)
    cr.add_argument("--mitm-flow-file", default=os.environ.get("MITM_FLOW_FILE"),
                    help="mitmdump -w output; watched to detect certificate pinning early")
    cr.add_argument("--preserve-app-state", action="store_true",
                    help="skip the session-start data wipe; resume against whatever state "
                         "the app is already in (e.g. onboarding already completed by hand) "
                         "instead of facing a one-time onboarding flow the crawler can't "
                         "get past on its own")
    cr.add_argument("--bootstrap-content-desc", default=None,
                    help="accessibility-id of an element to tap once after every reset, "
                         "before replaying the rest of a queued path — e.g. 'Properties', "
                         "so a crawl bootstrapped into a non-default section (via "
                         "--preserve-app-state) keeps returning there instead of to the "
                         "app's own default tab")
    cr.set_defaults(func=_cmd_crawl)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "command", None) == "crawl" and not args.package:
        print("error: --package is required (set BAYUT_APP_PACKAGE in .env)", file=sys.stderr)
        return 2
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, RuntimeError, AdbError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted — partial reports were not written", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
