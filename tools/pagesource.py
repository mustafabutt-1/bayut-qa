"""Android page-source parsing shared by crawler.py, prober.py and crawl_safety.py.

Pure functions over a UiAutomator XML dump. No device, no Appium, no network — so
every consumer of this module can be tested against fixture XML files.

CLI
---
    python tools/pagesource.py parse --page-source tests/fixtures/page_source/x.xml
    python tools/pagesource.py fingerprint --page-source x.xml
    python tools/pagesource.py diff --baseline a.xml --candidate b.xml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Element",
    "parse_page_source",
    "parse_page_source_file",
    "tappable",
    "screen_fingerprint",
    "identifier_set",
]

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")

# Attributes UiAutomator emits as "true"/"false" strings.
_BOOL_ATTRS = (
    "checkable",
    "checked",
    "clickable",
    "enabled",
    "focusable",
    "focused",
    "scrollable",
    "long-clickable",
    "password",
    "selected",
    "displayed",
)


def _as_bool(value: str | None) -> bool:
    return value == "true"


@dataclass(frozen=True)
class Element:
    """One node of a UiAutomator hierarchy dump."""

    klass: str
    package: str
    resource_id: str
    content_desc: str
    text: str
    bounds: tuple[int, int, int, int] | None
    clickable: bool
    long_clickable: bool
    enabled: bool
    scrollable: bool
    checkable: bool
    checked: bool
    selected: bool
    displayed: bool
    index: int
    xpath: str
    depth: int
    ancestors_clickable: bool = False
    raw: dict[str, str] = field(default_factory=dict, repr=False)

    # -- derived ---------------------------------------------------------

    @property
    def center(self) -> tuple[int, int] | None:
        """Tap point. None when bounds are missing or degenerate (zero-area)."""
        if self.bounds is None:
            return None
        x1, y1, x2, y2 = self.bounds
        if x2 <= x1 or y2 <= y1:
            return None
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def area(self) -> int:
        if self.bounds is None:
            return 0
        x1, y1, x2, y2 = self.bounds
        return max(0, x2 - x1) * max(0, y2 - y1)

    @property
    def short_id(self) -> str:
        """The id fragment after the ':id/' prefix, or '' when absent."""
        if "/" in self.resource_id:
            return self.resource_id.rsplit("/", 1)[1]
        return ""

    @property
    def stable_identifier(self) -> str | None:
        """Locale- and content-independent identity, or None if the element has none.

        Deliberately excludes ``text``: text changes with locale and with listing
        content, so a fingerprint built on it would report a new screen every time a
        different property loaded.
        """
        if self.content_desc:
            return f"desc={self.content_desc}"
        if self.resource_id:
            return f"id={self.resource_id}"
        return None

    @property
    def locator_strategy(self) -> str:
        """Best available locator, per the priority in CLAUDE.md."""
        if self.content_desc:
            return "accessibility id"
        if self.resource_id:
            return "resource-id"
        if self.text:
            return "uiautomator"
        return "xpath"

    @property
    def locator_value(self) -> str:
        if self.content_desc:
            return self.content_desc
        if self.resource_id:
            return self.resource_id
        if self.text:
            return f'new UiSelector().text("{self.text}")'
        return self.xpath

    @property
    def stability(self) -> str:
        """HIGH / MEDIUM / LOW / FRAGILE — feeds context/locator-quality.md."""
        if self.content_desc:
            return "HIGH"
        if self.resource_id:
            return "MEDIUM"
        if self.text:
            return "LOW"  # breaks under Arabic locale
        return "FRAGILE"

    @property
    def label(self) -> str:
        """Best human-readable name, for reports."""
        return self.content_desc or self.text or self.short_id or self.klass.rsplit(".", 1)[-1]

    def to_dict(self) -> dict[str, object]:
        return {
            "class": self.klass,
            "package": self.package,
            "resource_id": self.resource_id,
            "content_desc": self.content_desc,
            "text": self.text,
            "bounds": list(self.bounds) if self.bounds else None,
            "center": list(self.center) if self.center else None,
            "clickable": self.clickable,
            "long_clickable": self.long_clickable,
            "enabled": self.enabled,
            "scrollable": self.scrollable,
            "checkable": self.checkable,
            "checked": self.checked,
            "selected": self.selected,
            "xpath": self.xpath,
            "depth": self.depth,
            "locator_strategy": self.locator_strategy,
            "locator_value": self.locator_value,
            "stability": self.stability,
            "label": self.label,
        }


def _parse_bounds(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    m = _BOUNDS_RE.match(value)
    if not m:
        return None
    x1, y1, x2, y2 = (int(g) for g in m.groups())
    return (x1, y1, x2, y2)


def _xpath_for(node: ET.Element, parent_xpath: str, sibling_index: int) -> str:
    klass = node.get("class") or node.tag
    return f"{parent_xpath}/{klass}[{sibling_index}]"


def parse_page_source(xml_text: str) -> list[Element]:
    """Parse a UiAutomator XML dump into a flat, document-ordered element list.

    Raises ValueError on malformed XML rather than returning an empty list — a silent
    empty parse would look identical to "the screen has no elements", and the crawler
    would record a screen that does not exist.
    """
    if not xml_text or not xml_text.strip():
        raise ValueError("page source is empty")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:  # pragma: no cover - depends on device output
        raise ValueError(f"page source is not valid XML: {exc}") from exc

    elements: list[Element] = []

    def walk(node: ET.Element, parent_xpath: str, depth: int, ancestor_clickable: bool) -> None:
        counts: dict[str, int] = {}
        for child in list(node):
            klass = child.get("class") or child.tag
            counts[klass] = counts.get(klass, 0) + 1
            xpath = _xpath_for(child, parent_xpath, counts[klass])
            attrs = dict(child.attrib)
            clickable = _as_bool(attrs.get("clickable"))
            el = Element(
                klass=klass,
                package=attrs.get("package", ""),
                resource_id=attrs.get("resource-id", ""),
                content_desc=attrs.get("content-desc", ""),
                text=attrs.get("text", ""),
                bounds=_parse_bounds(attrs.get("bounds")),
                clickable=clickable,
                long_clickable=_as_bool(attrs.get("long-clickable")),
                enabled=attrs.get("enabled", "true") == "true",
                scrollable=_as_bool(attrs.get("scrollable")),
                checkable=_as_bool(attrs.get("checkable")),
                checked=_as_bool(attrs.get("checked")),
                selected=_as_bool(attrs.get("selected")),
                displayed=attrs.get("displayed", "true") == "true",
                index=int(attrs.get("index", "0") or 0),
                xpath=xpath,
                depth=depth,
                ancestors_clickable=ancestor_clickable,
                raw={k: v for k, v in attrs.items() if k in _BOOL_ATTRS or k in
                     ("text", "resource-id", "content-desc", "class", "package", "bounds")},
            )
            elements.append(el)
            walk(child, xpath, depth + 1, ancestor_clickable or clickable)

    walk(root, "/hierarchy", 0, False)
    return elements


def parse_page_source_file(path: str | Path) -> list[Element]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"page source not found: {p}")
    return parse_page_source(p.read_text(encoding="utf-8", errors="replace"))


def tappable(elements: list[Element], *, include_nested: bool = False) -> list[Element]:
    """Elements a crawl could actually tap.

    Excludes disabled elements, zero-area elements, and — unless ``include_nested`` —
    clickable elements nested inside another clickable element, since tapping the child
    usually just re-triggers the parent and doubles the action budget for nothing.
    """
    out = []
    for el in elements:
        if not (el.clickable or el.long_clickable):
            continue
        if not el.enabled or el.center is None:
            continue
        if el.ancestors_clickable and not include_nested:
            continue
        out.append(el)
    return out


def identifier_set(elements: list[Element], *, mode: str = "structural") -> list[str]:
    """Sorted set of identifiers present on a screen.

    ``structural`` — ``resource-id`` only. Resource IDs are compile-time names, so this
    set is **locale-invariant**: the same screen fingerprints identically in English and
    Arabic. Use it for screen identity.

    ``full`` — resource-id plus ``content-desc``. content-desc is a *localized* string
    (TalkBack reads it aloud), so this set changes with locale by design. Comparing the
    two locales' full fingerprints is how locale divergence becomes visible.
    """
    if mode not in ("structural", "full"):
        raise ValueError(f"mode must be 'structural' or 'full', got {mode!r}")
    ids: set[str] = set()
    for el in elements:
        if el.resource_id:
            ids.add(f"id={el.resource_id}")
        # Union, not fallback: an element with both a resource-id and a content-desc
        # still contributes its localized label to the full set, otherwise "full" would
        # equal "structural" on any screen where every labelled element also has an id.
        if mode == "full" and el.content_desc:
            ids.add(f"desc={el.content_desc}")
    return sorted(ids)


def screen_fingerprint(elements: list[Element], *, length: int = 12,
                       mode: str = "structural") -> str:
    """Identity of a screen: hash of its identifier set.

    ``text`` is always excluded, so the same screen showing different listings
    fingerprints identically. In the default ``structural`` mode ``content-desc`` is
    excluded too, so the same screen in Arabic also fingerprints identically — which is
    what makes "two states with the same fingerprint are the same screen" hold across
    locales.

    A screen with no resource IDs at all falls back to its class skeleton. That fallback
    is weak; callers should treat such a fingerprint as low-confidence and say so.
    """
    ids = identifier_set(elements, mode=mode)
    if not ids:
        ids = sorted({f"class={el.klass}@{el.depth}" for el in elements})
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return digest[:length]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_parse(args: argparse.Namespace) -> int:
    els = parse_page_source_file(args.page_source)
    taps = tappable(els)
    if args.json:
        print(json.dumps([e.to_dict() for e in (taps if args.tappable_only else els)], indent=2, ensure_ascii=False))
        return 0
    print(f"file         : {args.page_source}")
    print(f"elements     : {len(els)}")
    print(f"tappable     : {len(taps)}")
    print(f"fingerprint  : {screen_fingerprint(els)}")
    by_stability: dict[str, int] = {}
    for e in els:
        by_stability[e.stability] = by_stability.get(e.stability, 0) + 1
    print("stability    : " + ", ".join(f"{k}={v}" for k, v in sorted(by_stability.items())))
    print()
    rows = taps if args.tappable_only else els
    print(f"{'stability':<10} {'strategy':<17} {'label':<34} locator")
    print("-" * 100)
    for e in rows:
        print(f"{e.stability:<10} {e.locator_strategy:<17} {e.label[:33]:<34} {e.locator_value[:40]}")
    return 0


def _cmd_fingerprint(args: argparse.Namespace) -> int:
    els = parse_page_source_file(args.page_source)
    print(f"structural (locale-invariant): {screen_fingerprint(els, mode='structural')}")
    print(f"full (includes content-desc) : {screen_fingerprint(els, mode='full')}")
    if args.show_ids:
        for i in identifier_set(els, mode=args.mode):
            print(f"  {i}")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    base = identifier_set(parse_page_source_file(args.baseline), mode=args.mode)
    cand = identifier_set(parse_page_source_file(args.candidate), mode=args.mode)
    removed = [i for i in base if i not in cand]
    added = [i for i in cand if i not in base]
    print(f"baseline identifiers : {len(base)}")
    print(f"candidate identifiers: {len(cand)}")
    print(f"removed              : {len(removed)}")
    print(f"added                : {len(added)}")
    for i in removed:
        print(f"  - {i}")
    for i in added:
        print(f"  + {i}")
    # Removed identifiers are the ones that break existing tests silently.
    return 1 if removed else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pagesource.py",
        description="Parse and fingerprint Android UiAutomator page-source dumps. "
                    "Runs entirely offline against XML files.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("parse", help="list elements, locators and stability")
    sp.add_argument("--page-source", required=True, help="path to a UiAutomator XML dump")
    sp.add_argument("--tappable-only", action="store_true", help="only elements a crawl could tap")
    sp.add_argument("--json", action="store_true", help="machine-readable output")
    sp.set_defaults(func=_cmd_parse)

    sf = sub.add_parser("fingerprint", help="print the screen fingerprint")
    sf.add_argument("--page-source", required=True)
    sf.add_argument("--show-ids", action="store_true", help="also list the identifiers hashed")
    sf.add_argument("--mode", choices=["structural", "full"], default="structural",
                    help="which identifier set --show-ids prints")
    sf.set_defaults(func=_cmd_fingerprint)

    sd = sub.add_parser("diff", help="diff identifier sets between two dumps (exit 1 if any removed)")
    sd.add_argument("--baseline", required=True)
    sd.add_argument("--candidate", required=True)
    sd.add_argument("--mode", choices=["structural", "full"], default="structural",
                    help="structural ignores localized content-desc; use full to see locale drift")
    sd.set_defaults(func=_cmd_diff)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
