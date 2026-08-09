"""Tap safety guard for every agent that drives the live Bayut app.

Imported by ``crawler.py`` (PASSIVE mode) and ``prober.py`` (PROBE mode). Both tap
elements on a production app signed in with a real test account, so both go through
this one guard. One place to audit, one place to test.

Posture
-------
Default-deny. An element is tapped only when it matches an **allow** rule and matches
no **block** rule. Everything else is UNCERTAIN and is logged, not tapped.

    BLOCK      matched a blocklist rule            -> never tapped, in any mode
    ALLOW      matched an allow rule, no block hit -> tapped
    UNCERTAIN  matched nothing                     -> tapped only in permissive mode

Block always beats allow. There is no flag that disables the blocklist.

The single unrecoverable mistake this module exists to prevent is tapping a
contact-agent control: that sends a real lead to a real Dubai agency, costs money, and
ends the programme's credibility. Everything else here is secondary.

CLI
---
    python tools/crawl_safety.py selftest
    python tools/crawl_safety.py rules
    python tools/crawl_safety.py check --page-source dump.xml
    python tools/crawl_safety.py explain --text "Call" --class android.widget.Button
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from pagesource import Element, parse_page_source_file, tappable

__all__ = [
    "Verdict",
    "SafetyDecision",
    "SafetyPolicy",
    "DEFAULT_BLOCK_RULES",
    "DEFAULT_ALLOW_RULES",
]

Verdict = Literal["BLOCK", "ALLOW", "UNCERTAIN"]

# Fields a rule may match against, mapped to the Element attribute they read.
_MATCH_FIELDS = {
    "text": "text",
    "content_desc": "content_desc",
    "resource_id": "resource_id",
    "klass": "klass",
    "package": "package",
}


_WORD_SEPARATORS = re.compile(r"[_\-./:]+")


def _match_candidates(value: str) -> tuple[str, ...]:
    """The raw value plus a word-normalised variant, so identifiers match too."""
    if not value:
        return ("",)
    normalised = _WORD_SEPARATORS.sub(" ", value)
    return (value,) if normalised == value else (value, normalised)


@dataclass(frozen=True)
class Rule:
    """One safety rule. Regexes are matched case-insensitively with re.search."""

    id: str
    category: str
    reason: str
    text: str | None = None
    content_desc: str | None = None
    resource_id: str | None = None
    klass: str | None = None
    package: str | None = None
    any_field: str | None = None  # matched against text, desc, resource-id together

    def matches(self, el: Element) -> tuple[bool, str]:
        """Return (matched, which-field-matched).

        Each value is tested both raw and word-normalised. Normalisation matters:
        ``call_agent_button`` does not match ``\\bcall\\b`` because ``_`` is a word
        character, and identifiers are exactly where the dangerous controls live.
        """
        for rule_field, el_attr in _MATCH_FIELDS.items():
            pattern = getattr(self, rule_field)
            if not pattern:
                continue
            value = getattr(el, el_attr) or ""
            for candidate in _match_candidates(value):
                if re.search(pattern, candidate, re.IGNORECASE):
                    return True, f"{rule_field}={value!r}"
        if self.any_field:
            haystack = " | ".join((el.text or "", el.content_desc or "", el.resource_id or ""))
            for candidate in _match_candidates(haystack):
                if re.search(self.any_field, candidate, re.IGNORECASE):
                    return True, f"any={haystack!r}"
        return False, ""


@dataclass(frozen=True)
class SafetyDecision:
    verdict: Verdict
    rule_id: str | None
    category: str | None
    reason: str
    matched_on: str
    element_label: str
    locator: str

    @property
    def tappable(self) -> bool:
        return self.verdict == "ALLOW"

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "rule_id": self.rule_id,
            "category": self.category,
            "reason": self.reason,
            "matched_on": self.matched_on,
            "element": self.element_label,
            "locator": self.locator,
        }


# ---------------------------------------------------------------------------
# BLOCKLIST — the hard stop. Never edit to "unblock" something for convenience.
#
# Patterns cover EN and AR. Arabic labels are [ASSUMED — verify] against the shipped
# Arabic build; app-cartographer must confirm them in its first ar-AE crawl and any
# missing form is a safety gap, so the AR crawl runs in strict mode only.
#
# Deliberately NOT blocked, because they are the app's core navigation and blocking
# them would stop the crawl dead: bare "Buy" / "شراء" (purpose toggle), "Save" /
# "Favourite" (non-destructive, reversible), "Search", "Filter".
# ---------------------------------------------------------------------------

DEFAULT_BLOCK_RULES: tuple[Rule, ...] = (
    # --- Lead generation: the money-losing category -------------------------
    Rule(
        "BLOCK-LEAD-CALL", "lead_contact",
        "Places a real phone call to a real estate agent — a billable lead.",
        any_field=r"\b(call|call\s*agent|call\s*now|phone|dial|tel)\b|اتصال|اتصل|هاتف|الاتصال",
    ),
    Rule(
        "BLOCK-LEAD-WHATSAPP", "lead_contact",
        "Opens WhatsApp with a prefilled message to an agency — a billable lead.",
        any_field=r"whats\s*app|wa\.me|واتساب|واتس\s*اب",
    ),
    Rule(
        "BLOCK-LEAD-EMAIL", "lead_contact",
        "Sends an email enquiry to an agency — a billable lead.",
        any_field=r"\b(e-?mail|send\s*(e-?mail|message|enquiry|inquiry)|mailto)\b|البريد\s*الإلكتروني|راسل",
    ),
    Rule(
        "BLOCK-LEAD-CONTACT", "lead_contact",
        "Any contact / enquiry affordance reaches a real agent.",
        any_field=r"\b(contact\w*|enquir\w*|inquir\w*|request\s*(info\w*|details|callback)|"
                  r"get\s*in\s*touch)\b|تواصل|استفسار|طلب\s*معلومات",
    ),
    Rule(
        "BLOCK-LEAD-VIEWING", "lead_contact",
        "Books a physical viewing with an agent.",
        any_field=r"\b(book\s*(a\s*)?viewing|schedule\s*(a\s*)?(visit|tour|viewing)|arrange\s*viewing)\b"
                  r"|حجز\s*موعد|طلب\s*معاينة",
    ),
    Rule(
        "BLOCK-LEAD-REGISTER-INTEREST", "lead_contact",
        "New-projects 'register interest' is a lead form.",
        any_field=r"register\s*(your\s*)?interest|سجل\s*اهتمامك",
    ),
    Rule(
        "BLOCK-LEAD-URI", "lead_contact",
        "Element carries a tel:/mailto:/whatsapp: URI — external contact intent.",
        any_field=r"(tel:|mailto:|whatsapp:|sms:)",
    ),
    Rule(
        "BLOCK-LEAD-PHONE-NUMBER", "lead_contact",
        "Element renders a phone number; tapping it is likely to dial.",
        any_field=r"(\+971|00971|\b05\d)\s?\d{2}\s?\d{3}\s?\d{4}",
    ),
    Rule(
        "BLOCK-FORM-SUBMIT", "lead_contact",
        "Submitting any form on an LDP or agent page files an enquiry.",
        any_field=r"\b(submit|send\s*request|send\s*now)\b|إرسال|ارسال",
    ),

    # --- Session and account destruction ------------------------------------
    Rule(
        "BLOCK-LOGOUT", "session",
        "Destroys the session and kills the crawl mid-run.",
        any_field=r"\b(log\s*out|sign\s*out|logout|signout)\b|تسجيل\s*الخروج",
    ),
    Rule(
        "BLOCK-ACCOUNT-DELETE", "destructive",
        "Irreversible account deletion.",
        any_field=r"\b(delete|close|deactivate)\s*(my\s*)?account\b|حذف\s*الحساب",
    ),

    # --- Destructive data actions -------------------------------------------
    Rule(
        "BLOCK-DELETE", "destructive",
        "Deletes saved data (saved search, favourite, alert, history).",
        any_field=r"\b(delete|remove|clear\s*all|unsave|discard)\b|حذف|إزالة|ازالة|مسح\s*الكل",
    ),

    # --- Moderation queues ---------------------------------------------------
    Rule(
        "BLOCK-REPORT", "moderation",
        "Reaches a human moderation queue at Bayut.",
        any_field=r"\b(report|flag)\s*(this\s*)?(listing|property|agent|agency|ad)?\b|إبلاغ|ابلاغ|بلاغ|شكوى",
    ),

    # --- Money ---------------------------------------------------------------
    Rule(
        "BLOCK-COMMERCE", "commerce",
        "Payment, subscription or upgrade flow. Note: bare 'Buy' is the purpose "
        "toggle and is intentionally NOT matched here.",
        any_field=r"\b(buy\s*now|purchase|checkout|check\s*out|payment|pay\s*now|subscribe|"
                  r"subscription|upgrade\s*(to|plan)|add\s*card|billing|credits)\b"
                  r"|الدفع|اشتراك|ترقية|شراء\s*الآن",
    ),

    # --- Surfaces we must not corrupt before testing them --------------------
    Rule(
        "BLOCK-NOTIFICATION-OPTIN", "notifications",
        "Opting in corrupts the push-notification test surface for later suites.",
        any_field=r"\b(allow|enable|turn\s*on|manage)\s*notifications?\b|\bnotify\s*me\b|"
                  r"\b(create|set|manage|save)\s*(an?\s*)?alerts?\b|"
                  r"تفعيل\s*الإشعارات|السماح\s*بالإشعارات|الإشعارات",
    ),

    # --- Leaving the app -----------------------------------------------------
    Rule(
        "BLOCK-SHARE", "external",
        "Opens the OS share sheet; hard to return from reliably.",
        any_field=r"\b(share)\b|مشاركة|شارك",
    ),
    Rule(
        "BLOCK-EXTERNAL-LINK", "external",
        "Leaves the app for a browser, store listing, or social profile.",
        any_field=r"\b(open\s*in\s*browser|view\s*on\s*web|rate\s*(us|this\s*app)|"
                  r"play\s*store|app\s*store|terms|privacy\s*policy|facebook|instagram|twitter|linkedin)\b"
                  r"|شروط\s*الاستخدام|سياسة\s*الخصوصية",
    ),
    Rule(
        "BLOCK-EXTERNAL-PACKAGE", "external",
        "Element belongs to another app (dialer, WhatsApp, browser, store).",
        package=r"^(com\.whatsapp|com\.android\.(dialer|phone|chrome|browser|vending|mms)|"
                r"com\.google\.android\.(gm|apps\.maps|youtube)|com\.android\.systemui)",
    ),
    Rule(
        "BLOCK-SYSTEM-PERMISSION-GRANT", "system",
        "System permission dialog. The crawler dismisses these deliberately rather "
        "than tapping a grant/deny button by accident.",
        package=r"^com\.android\.permissioncontroller|^com\.google\.android\.permissioncontroller",
    ),
)


# ---------------------------------------------------------------------------
# ALLOWLIST — navigation and read-only surfaces. Extend via YAML, not by widening
# these patterns, so the shipped defaults stay reviewable.
# ---------------------------------------------------------------------------

DEFAULT_ALLOW_RULES: tuple[Rule, ...] = (
    Rule("ALLOW-NAV-BACK", "navigation", "Back / close / cancel / dismiss — always safe.",
         any_field=r"\b(back|close|cancel|dismiss|skip|not\s*now|later|x)\b|رجوع|إغلاق|إلغاء|تخطي"),
    Rule("ALLOW-NAV-TABS", "navigation", "Bottom-tab navigation.",
         any_field=r"\b(home|explore|discover|search|saved|favou?rites?|shortlist|profile|account|menu|more)\b"
                   r"|الرئيسية|بحث|المفضلة|حسابي"),
    Rule("ALLOW-SEARCH", "search", "Search entry, submit and suggestions.",
         any_field=r"\b(search|find|suggestion|recent\s*search|autocomplete|location)\b|بحث|الموقع"),
    Rule("ALLOW-PURPOSE", "search", "Buy / Rent purpose toggle — core navigation, not commerce.",
         text=r"^\s*(buy|rent|commercial|residential|new\s*projects?)\s*$|^\s*(شراء|إيجار|تجاري|سكني)\s*$"),
    Rule("ALLOW-FILTERS", "filters", "Filter sheet controls and apply.",
         any_field=r"\b(filter\w*|refine\w*|sort\w*|appl(y|ied)|show\s*[\d,]+|show\s*propert\w*|"
                   r"reset|clear\s*filter\w*|done)\b|الفلاتر|تصفية|ترتيب|تطبيق"),
    Rule("ALLOW-FILTER-VALUES", "filters", "Filter option chips and rows.",
         any_field=r"\b(apartment|villa|townhouse|penthouse|studio|bedroom|bathroom|beds?|baths?|"
                   r"furnished|unfurnished|ready|off[\s-]?plan|yearly|monthly|weekly|daily|"
                   r"sqft|sqm|price|area|amenit|trucheck|verified|any)\b"
                   r"|شقة|فيلا|غرف|حمامات|مفروش|جاهز|سنوي|السعر|المساحة"),
    Rule("ALLOW-RESULTS", "results", "Listing cards, result list and view toggles.",
         any_field=r"\b(listing\w*|propert\w*_?card|card_?container|result\w*|map\w*|list\s*view|"
                   r"gallery|photos?|images?|next|previous|pages?|load\s*more|view\s*more|see\s*all)\b"
                   r"|العقار|الخريطة|القائمة|صور"),
    Rule("ALLOW-LDP-READONLY", "listing", "Read-only listing-detail sections.",
         any_field=r"\b(overview|descriptions?|amenit\w*|features?|floor\s*plans?|locations?|map\w*|"
                   r"trends?|similar|nearby|read\s*more|show\s*more|expand)\b"
                   r"|الوصف|المرافق|المخطط|اقرأ\s*المزيد"),
    Rule("ALLOW-SETTINGS-READONLY", "settings", "Language / currency / unit switchers.",
         any_field=r"\b(language|currency|area\s*unit|sq\s*ft|sq\s*m|english|arabic|settings|preferences)\b"
                   r"|اللغة|العملة|الإعدادات|العربية|الإنجليزية"),
    Rule("ALLOW-SCROLL-CONTAINER", "navigation", "Scrollable containers — scrolled, not activated.",
         klass=r"(RecyclerView|ScrollView|ViewPager|HorizontalScrollView)$"),
)


DEFAULT_CONFIG_PATH = Path("context/crawl-allowlist.yaml")


@dataclass
class SafetyPolicy:
    """Evaluates elements against the block and allow rule sets."""

    block_rules: list[Rule] = field(default_factory=lambda: list(DEFAULT_BLOCK_RULES))
    allow_rules: list[Rule] = field(default_factory=lambda: list(DEFAULT_ALLOW_RULES))
    app_package: str | None = None
    permissive: bool = False

    # -- construction ----------------------------------------------------

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        *,
        app_package: str | None = None,
        permissive: bool = False,
    ) -> "SafetyPolicy":
        """Defaults, plus optional YAML extensions.

        The YAML may only *add* rules. There is no mechanism to remove a default block
        rule, by design — see the module docstring.
        """
        policy = cls(app_package=app_package, permissive=permissive)
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if not path.is_file():
            return policy
        try:
            import yaml  # local import: config is optional, PyYAML may be absent
        except ImportError as exc:
            raise RuntimeError(
                f"{path} exists but PyYAML is not installed; run: pip install PyYAML"
            ) from exc
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for section, target in (("block", policy.block_rules), ("allow", policy.allow_rules)):
            for raw in data.get(section, []) or []:
                if "id" not in raw:
                    raise ValueError(f"{path}: every {section} rule needs an 'id'")
                match = raw.get("match", {}) or {}
                unknown = set(match) - set(_MATCH_FIELDS) - {"any_field"}
                if unknown:
                    raise ValueError(f"{path}: rule {raw['id']} has unknown match fields: {sorted(unknown)}")
                target.append(
                    Rule(
                        id=str(raw["id"]),
                        category=str(raw.get("category", section)),
                        reason=str(raw.get("reason", "(no reason given)")),
                        **{k: str(v) for k, v in match.items()},
                    )
                )
        return policy

    # -- evaluation ------------------------------------------------------

    def evaluate(self, el: Element) -> SafetyDecision:
        """Decide whether this element may be tapped. Block always wins."""
        label = el.label
        locator = f"{el.locator_strategy}={el.locator_value}"

        for rule in self.block_rules:
            hit, where = rule.matches(el)
            if hit:
                return SafetyDecision("BLOCK", rule.id, rule.category, rule.reason, where, label, locator)

        # Foreign package with no explicit block rule is still foreign.
        if self.app_package and el.package and el.package != self.app_package:
            return SafetyDecision(
                "BLOCK", "BLOCK-FOREIGN-PACKAGE", "external",
                f"Element belongs to {el.package}, not the app under test ({self.app_package}).",
                f"package={el.package!r}", label, locator,
            )

        for rule in self.allow_rules:
            hit, where = rule.matches(el)
            if hit:
                return SafetyDecision("ALLOW", rule.id, rule.category, rule.reason, where, label, locator)

        return SafetyDecision(
            "UNCERTAIN", None, None,
            "Matched no allow rule. Not tapped in strict mode — review and promote to "
            "context/crawl-allowlist.yaml if safe.",
            "", label, locator,
        )

    def may_tap(self, el: Element) -> tuple[bool, SafetyDecision]:
        """Final gate the crawler and prober call before every tap."""
        decision = self.evaluate(el)
        if decision.verdict == "BLOCK":
            return False, decision
        if decision.verdict == "ALLOW":
            return True, decision
        return self.permissive, decision

    def partition(self, elements: Iterable[Element]) -> dict[str, list[SafetyDecision]]:
        out: dict[str, list[SafetyDecision]] = {"ALLOW": [], "BLOCK": [], "UNCERTAIN": []}
        for el in elements:
            d = self.evaluate(el)
            out[d.verdict].append(d)
        return out


# ---------------------------------------------------------------------------
# Selftest — adversarial strings that MUST be blocked, and navigation strings that
# MUST NOT be. Run this before every crawl session; it needs no device and no fixture.
# ---------------------------------------------------------------------------

_MUST_BLOCK: tuple[tuple[str, str], ...] = (
    ("text", "Call"),
    ("text", "Call Agent"),
    ("text", "CALL NOW"),
    ("content_desc", "call_agent_button"),
    ("text", "WhatsApp"),
    ("text", "Whats App"),
    ("content_desc", "whatsapp_agent"),
    ("text", "Email"),
    ("text", "Send Email"),
    ("text", "Send Message"),
    ("text", "Contact Agent"),
    ("text", "Contact Us"),
    ("text", "Enquire Now"),
    ("text", "Request Callback"),
    ("text", "Book a Viewing"),
    ("text", "Schedule a Visit"),
    ("text", "Register Interest"),
    ("text", "Submit"),
    ("resource_id", "com.bayut.app:id/btn_submit_enquiry"),
    ("text", "+971 50 123 4567"),
    ("content_desc", "tel:+97150000000"),
    ("text", "Log out"),
    ("text", "Sign Out"),
    ("text", "Delete Account"),
    ("text", "Delete"),
    ("text", "Remove from Favourites"),
    ("text", "Clear All"),
    ("text", "Report this listing"),
    ("text", "Report Agent"),
    ("text", "Buy Now"),
    ("text", "Subscribe"),
    ("text", "Upgrade Plan"),
    ("text", "Checkout"),
    ("text", "Allow Notifications"),
    ("text", "Create Alert"),
    ("text", "Share"),
    ("text", "Rate this app"),
    ("text", "Privacy Policy"),
    # Arabic forms
    ("text", "اتصال"),
    ("text", "اتصل بالوكيل"),
    ("text", "واتساب"),
    ("text", "راسل"),
    ("text", "تواصل"),
    ("text", "استفسار"),
    ("text", "إرسال"),
    ("text", "تسجيل الخروج"),
    ("text", "حذف"),
    ("text", "إبلاغ"),
    ("text", "مشاركة"),
    ("text", "الدفع"),
    ("text", "تفعيل الإشعارات"),
)

_MUST_NOT_BLOCK: tuple[tuple[str, str], ...] = (
    ("text", "Buy"),
    ("text", "Rent"),
    ("text", "شراء"),
    ("text", "إيجار"),
    ("text", "Search"),
    ("text", "Filters"),
    ("text", "Apartment"),
    ("text", "Villa"),
    ("text", "Studio"),
    ("text", "Show 1,240 properties"),
    ("text", "Back"),
    ("text", "Map"),
    ("resource_id", "com.bayut.app:id/listing_card"),
)


def _synthetic(field_name: str, value: str, package: str = "com.bayut.app") -> Element:
    kwargs = {
        "klass": "android.widget.TextView",
        "package": package,
        "resource_id": "",
        "content_desc": "",
        "text": "",
        "bounds": (0, 0, 100, 100),
        "clickable": True,
        "long_clickable": False,
        "enabled": True,
        "scrollable": False,
        "checkable": False,
        "checked": False,
        "selected": False,
        "displayed": True,
        "index": 0,
        "xpath": "/hierarchy/synthetic[1]",
        "depth": 1,
    }
    kwargs[field_name] = value
    return Element(**kwargs)  # type: ignore[arg-type]


def run_selftest(verbose: bool = False) -> int:
    policy = SafetyPolicy(app_package="com.bayut.app")
    failures: list[str] = []

    for field_name, value in _MUST_BLOCK:
        d = policy.evaluate(_synthetic(field_name, value))
        if d.verdict != "BLOCK":
            failures.append(f"NOT BLOCKED: {field_name}={value!r} -> {d.verdict}")
        elif verbose:
            print(f"  BLOCK     {value!r:<34} {d.rule_id}")

    for field_name, value in _MUST_NOT_BLOCK:
        d = policy.evaluate(_synthetic(field_name, value))
        if d.verdict == "BLOCK":
            failures.append(f"OVER-BLOCKED: {field_name}={value!r} -> {d.rule_id} ({d.reason})")
        elif verbose:
            print(f"  {d.verdict:<9} {value!r:<34} {d.rule_id or '-'}")

    # Foreign packages must be blocked even with innocuous text.
    d = policy.evaluate(_synthetic("text", "OK", package="com.whatsapp"))
    if d.verdict != "BLOCK":
        failures.append("NOT BLOCKED: foreign package com.whatsapp")

    total = len(_MUST_BLOCK) + len(_MUST_NOT_BLOCK) + 1
    print(f"\nselftest: {total - len(failures)}/{total} assertions passed")
    for f in failures:
        print(f"  FAIL  {f}")
    if failures:
        print("\nDO NOT CRAWL until these pass.")
        return 1
    print("Blocklist and allowlist behave as specified. Safe to crawl.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_selftest(args: argparse.Namespace) -> int:
    return run_selftest(verbose=args.verbose)


def _cmd_rules(args: argparse.Namespace) -> int:
    policy = SafetyPolicy.load(args.config, app_package=args.app_package)
    print(f"BLOCK rules ({len(policy.block_rules)}) — never tapped in any mode\n")
    for r in policy.block_rules:
        print(f"  {r.id:<34} [{r.category}]")
        print(f"      {r.reason}")
    print(f"\nALLOW rules ({len(policy.allow_rules)}) — tapped in strict mode\n")
    for r in policy.allow_rules:
        print(f"  {r.id:<34} [{r.category}]  {r.reason}")
    print("\nAnything matching neither is UNCERTAIN: logged to context/crawl-uncertain.md, "
          "not tapped unless --allow-uncertain-taps is passed.")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    policy = SafetyPolicy.load(args.config, app_package=args.app_package, permissive=args.allow_uncertain_taps)
    elements = parse_page_source_file(args.page_source)
    targets = tappable(elements, include_nested=args.include_nested)
    parts = policy.partition(targets)

    if args.json:
        print(json.dumps(
            {k: [d.to_dict() for d in v] for k, v in parts.items()},
            indent=2, ensure_ascii=False,
        ))
    else:
        print(f"page source : {args.page_source}")
        print(f"tappable    : {len(targets)} of {len(elements)} elements")
        print(f"mode        : {'PERMISSIVE (uncertain WILL be tapped)' if policy.permissive else 'STRICT'}")
        print(f"ALLOW={len(parts['ALLOW'])}  BLOCK={len(parts['BLOCK'])}  UNCERTAIN={len(parts['UNCERTAIN'])}\n")
        for verdict in ("BLOCK", "ALLOW", "UNCERTAIN"):
            if not parts[verdict]:
                continue
            print(f"--- {verdict} ---")
            for d in parts[verdict]:
                rule = d.rule_id or "-"
                print(f"  {d.element_label[:36]:<38} {rule:<32} {d.locator[:44]}")
            print()

    if args.assert_no_block and parts["BLOCK"]:
        print(f"error: {len(parts['BLOCK'])} blocked element(s) present", file=sys.stderr)
        return 1
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    policy = SafetyPolicy.load(args.config, app_package=args.app_package)
    el = Element(
        klass=args.klass, package=args.package, resource_id=args.resource_id,
        content_desc=args.content_desc, text=args.text, bounds=(0, 0, 100, 100),
        clickable=True, long_clickable=False, enabled=True, scrollable=False,
        checkable=False, checked=False, selected=False, displayed=True,
        index=0, xpath="/hierarchy/explain[1]", depth=1,
    )
    d = policy.evaluate(el)
    print(f"verdict    : {d.verdict}")
    print(f"rule       : {d.rule_id or '(none matched)'}")
    print(f"category   : {d.category or '-'}")
    print(f"matched on : {d.matched_on or '-'}")
    print(f"reason     : {d.reason}")
    print(f"would tap  : {'yes' if d.verdict == 'ALLOW' else 'no (strict mode)'}")
    return 0 if d.verdict != "BLOCK" else 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="crawl_safety.py",
        description="Tap safety guard for live-app crawling and probing. Default-deny: "
                    "an element is tapped only if it matches an allow rule and no block rule.",
        epilog="Run `selftest` before every crawl session.",
    )
    p.add_argument("--config", default=None,
                   help=f"YAML rule extensions (default: {DEFAULT_CONFIG_PATH} if present)")
    p.add_argument("--app-package", default=None,
                   help="package of the app under test; anything else is blocked as foreign")
    sub = p.add_subparsers(dest="command", required=True)

    st = sub.add_parser("selftest", help="verify the blocklist catches known-dangerous labels")
    st.add_argument("--verbose", action="store_true")
    st.set_defaults(func=_cmd_selftest)

    rl = sub.add_parser("rules", help="print every active rule")
    rl.set_defaults(func=_cmd_rules)

    ck = sub.add_parser("check", help="classify every tappable element in a page-source dump")
    ck.add_argument("--page-source", required=True)
    ck.add_argument("--include-nested", action="store_true",
                    help="also evaluate clickables nested inside other clickables")
    ck.add_argument("--allow-uncertain-taps", action="store_true",
                    help="show the verdicts a PERMISSIVE crawl would act on")
    ck.add_argument("--assert-no-block", action="store_true",
                    help="exit 1 if any blocked element is present (for CI on fixtures)")
    ck.add_argument("--json", action="store_true")
    ck.set_defaults(func=_cmd_check)

    ex = sub.add_parser("explain", help="explain the verdict for one hypothetical element")
    ex.add_argument("--text", default="")
    ex.add_argument("--content-desc", dest="content_desc", default="")
    ex.add_argument("--resource-id", dest="resource_id", default="")
    ex.add_argument("--class", dest="klass", default="android.widget.TextView")
    ex.add_argument("--package", default="com.bayut.app")
    ex.set_defaults(func=_cmd_explain)
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
