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
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Literal

from pagesource import Element, parse_page_source_file, tappable

__all__ = [
    "Verdict",
    "Environment",
    "SafetyDecision",
    "SafetyPolicy",
    "LeadAuthorisation",
    "LeadNotAuthorised",
    "DEFAULT_BLOCK_RULES",
    "PRODUCTION_BLOCK_RULES",
    "DEFAULT_ALLOW_RULES",
    "LEAD_TEST_AGENCIES",
]

Verdict = Literal["BLOCK", "ALLOW", "UNCERTAIN"]
Environment = Literal["production", "staging"]

# The environment is PRODUCTION unless someone explicitly says otherwise, every time.
# There is no auto-detection and no "looks like staging" inference: guessing wrong in
# this direction creates real data on a live property portal.
DEFAULT_ENVIRONMENT: Environment = "production"

# The only agency whose listings may receive a generated lead. It is Bayut's own demo /
# testing agency, so a lead there reaches us, not a paying customer. Anything else is a
# real brokerage and a real bill.
LEAD_TEST_AGENCIES: tuple[str, ...] = ("Explorer Real Estate",)

# Seeded test location in production. Searches for lead tests should start here, because
# its inventory is ours. [ASSUMED — verify that Al Napoca listings are exclusively
# Explorer Real Estate; the checklist pairs them but does not state exclusivity.]
LEAD_TEST_LOCATION = "Al Napoca"

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
        # (?<!with[ _]) excludes the standalone "email" match only when it's the
        # OAuth-style "Continue with Email" / "Sign in with Email" auth-method
        # pattern (confirmed live: fl_continue_with_email false-positived here,
        # blocking a sign-in button that never contacts an agent). "send email",
        # "mailto", and the Arabic forms are unaffected — those stay unconditional.
        any_field=r"(?<!with[ _])\be-?mail\b|send\s*(e-?mail|message|enquiry|inquiry)|"
                  r"\bmailto\b|البريد\s*الإلكتروني|راسل",
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
# PRODUCTION BLOCKLIST — applied on top of the above whenever the environment is
# production, which is the default and the assumption until told otherwise.
#
# The rule these encode: **regression must not create data on production.** Every
# control below writes something that persists server-side — an account, a saved
# search, an alert, a report, a claim, a portfolio entry, a chat history, an LLM bill.
# On a staging environment these become tappable again by passing --environment staging.
#
# Reversible client-local state (favourites) is included too: on production it is
# attached to a real account, it pollutes Activity Log and recommendation signals, and
# the regression checklist itself treats favourites as persisted user data that must
# survive an app override.
# ---------------------------------------------------------------------------

PRODUCTION_BLOCK_RULES: tuple[Rule, ...] = (
    Rule(
        "PROD-BLOCK-SIGNUP", "data_creation",
        "Creates a real user account on production. Account deletion is a separate "
        "support burden and Apple/Google review surface.",
        any_field=r"\b(sign\s*up|signup|register|create\s*(an\s*)?account|join\s*now)\b"
                  r"|إنشاء\s*حساب|تسجيل\s*جديد",
    ),
    Rule(
        "PROD-BLOCK-SAVE-SEARCH", "data_creation",
        "Persists a saved search against the account and can trigger recurring alert "
        "emails and push notifications to a real inbox. Note: viewing the Saved Searches "
        "screen is read-only and stays allowed — only the save action is blocked.",
        any_field=r"\b(save\s*(this\s*)?search|save[_\s]search|alert\s*me\s*of\s*new)\b"
                  r"|حفظ\s*البحث",
    ),
    Rule(
        "PROD-BLOCK-FAVOURITE", "data_creation",
        "Writes to the account's favourites, pollutes Activity Log and recommendation "
        "signals, and the checklist treats favourites as persisted state that must "
        "survive an app override. The Favourites nav tab itself stays allowed.",
        any_field=r"\b(add\s*to\s*favou?rites?|remove\s*from\s*favou?rites?|"
                  r"btn[_\s]?favou?rite\w*|favou?rite[_\s]?button|save\s*propert\w*)\b"
                  r"|حفظ\s*العقار",
    ),
    Rule(
        "PROD-BLOCK-TRUESTIMATE-REPORT", "data_creation",
        "Generates a TruEstimate report: persisted against the account, emailed out, and "
        "it triggers the App Review bottom sheet. The TruEstimate landing screen is "
        "read-only and stays allowed — only generation and download are blocked.",
        any_field=r"\b(generate\s*(a\s*)?report|new\s*report|create\s*report|"
                  r"download\s*report|get\s*(my\s*)?(valuation|estimate)|confirm\s*details)\b",
    ),
    Rule(
        "PROD-BLOCK-PORTFOLIO", "data_creation",
        "Adds a property to the TruEstimate Portfolio — persisted account data. The "
        "Portfolio tab itself stays allowed.",
        any_field=r"\badd\s*to\s*portfolio\b",
    ),
    Rule(
        "PROD-BLOCK-CLAIM-TRANSACTION", "data_creation",
        "Submits a Dubai Transactions claim. Reaches Nova for human moderation and "
        "locks the transaction for other agents.",
        any_field=r"\b(claim\s*transaction\w*|claim\s*for\s*(yourself|an?\s*agent)|"
                  r"resubmit\s*claim|submit\s*claim)\b",
    ),
    Rule(
        "PROD-BLOCK-SELLER-LEADS", "data_creation",
        "Seller-leads / Sell My Property form creates a real seller lead.",
        any_field=r"\b(sell\s*my\s*propert\w*|seller\s*lead\w*|list\s*my\s*propert\w*)\b"
                  r"|بيع\s*عقاري",
    ),
    Rule(
        "PROD-BLOCK-BAYUTGPT-SEND", "data_creation",
        "Sends a BayutGPT query: costs a real LLM call and persists chat history against "
        "the account.",
        any_field=r"\bbayut\s*gpt\b|\b(send\s*query|ask\s*bayut)\b",
    ),
    Rule(
        "PROD-BLOCK-PROFILE-EDIT", "data_creation",
        "Edits the real account profile.",
        any_field=r"\b(edit\s*profile|update\s*profile|save\s*changes)\b|تعديل\s*الملف",
    ),
    Rule(
        "PROD-BLOCK-SHARE-REPORT", "data_creation",
        "Share Report / Share Transactions / Share Story generate a persisted shareable "
        "artifact and reach external platforms.",
        any_field=r"\b(share\s*(report|transaction\w*|stor(y|ies)|achievement))\b",
    ),
)
# Note: "Contact Us" needs no production rule — BLOCK-LEAD-CONTACT already catches it in
# every environment. Rules that could never fire are worse than absent: they read as
# coverage that is not there.


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


class LeadNotAuthorised(RuntimeError):
    """Raised when a lead test is attempted without an allowlisted agency on screen."""


@dataclass(frozen=True)
class LeadAuthorisation:
    allowed: bool
    agency_seen: str | None
    reason: str


@dataclass
class SafetyPolicy:
    """Evaluates elements against the block and allow rule sets."""

    block_rules: list[Rule] = field(default_factory=lambda: list(DEFAULT_BLOCK_RULES))
    production_block_rules: list[Rule] = field(
        default_factory=lambda: list(PRODUCTION_BLOCK_RULES))
    allow_rules: list[Rule] = field(default_factory=lambda: list(DEFAULT_ALLOW_RULES))
    app_package: str | None = None
    permissive: bool = False
    environment: Environment = DEFAULT_ENVIRONMENT
    lead_test_agencies: tuple[str, ...] = LEAD_TEST_AGENCIES
    # Set only inside a `lead_test` block. Never settable by config or CLI.
    _lead_auth: LeadAuthorisation | None = field(default=None, repr=False)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    # -- construction ----------------------------------------------------

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        *,
        app_package: str | None = None,
        permissive: bool = False,
        environment: Environment = DEFAULT_ENVIRONMENT,
    ) -> "SafetyPolicy":
        """Defaults, plus optional YAML extensions.

        The YAML may only *add* rules. There is no mechanism to remove a default block
        rule, by design — see the module docstring.
        """
        if environment not in ("production", "staging"):
            raise ValueError(f"environment must be 'production' or 'staging', "
                             f"got {environment!r}")
        policy = cls(app_package=app_package, permissive=permissive, environment=environment)
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
        for section, target in (("block", policy.block_rules),
                                ("production_block", policy.production_block_rules),
                                ("allow", policy.allow_rules)):
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
                # The single, evidence-gated exemption: inside an authorised lead test,
                # lead controls become tappable — and only lead controls, and only when
                # an allowlisted agency was found on the screen itself.
                if rule.category == "lead_contact" and self._lead_auth is not None:
                    return SafetyDecision(
                        "ALLOW", f"ALLOW-LEAD-AUTHORISED",
                        "lead_contact",
                        f"Lead test authorised against {self._lead_auth.agency_seen!r}, "
                        f"Bayut's own demo agency. Would otherwise be {rule.id}.",
                        where, label, locator,
                    )
                return SafetyDecision("BLOCK", rule.id, rule.category, rule.reason, where, label, locator)

        if self.is_production:
            for rule in self.production_block_rules:
                hit, where = rule.matches(el)
                if hit:
                    return SafetyDecision(
                        "BLOCK", rule.id, rule.category,
                        f"[PRODUCTION] {rule.reason}", where, label, locator,
                    )

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

    # -- lead authorisation ----------------------------------------------

    def authorise_lead(self, elements: Iterable[Element]) -> LeadAuthorisation:
        """Decide whether a lead may be generated from the screen currently displayed.

        The agency name is read out of the page source by this method. The caller does
        not get to assert which agency it is looking at — that is the whole point. A
        test that says "trust me, this is Explorer Real Estate" is exactly how a real
        brokerage ends up with a fake enquiry.
        """
        elements = list(elements)
        haystack = " | ".join(
            f"{el.text or ''} {el.content_desc or ''}" for el in elements
        )
        for agency in self.lead_test_agencies:
            if re.search(re.escape(agency), haystack, re.IGNORECASE):
                return LeadAuthorisation(
                    True, agency,
                    f"{agency!r} is present on the current screen and is on the lead "
                    f"allowlist (Bayut's own demo/testing agency).",
                )
        return LeadAuthorisation(
            False, None,
            f"No allowlisted agency found on the current screen. Allowed: "
            f"{list(self.lead_test_agencies)}. Generating a lead here would send a real, "
            f"billable enquiry to a real brokerage. Search {LEAD_TEST_LOCATION!r} and "
            f"open a listing from an allowlisted agency first.",
        )

    @contextmanager
    def lead_test(self, elements: Iterable[Element]) -> Iterator[LeadAuthorisation]:
        """Scope in which lead controls are tappable. Raises unless the screen proves it.

        Usage is deliberately awkward — you must hand it the live page source:

            with policy.lead_test(parse_page_source(driver.page_source)) as auth:
                ...tap the Call / Email / WhatsApp CTA...

        The exemption covers `lead_contact` rules only. Logout, delete, moderation,
        commerce and every production data-creation rule stay blocked inside the block.
        """
        auth = self.authorise_lead(elements)
        if not auth.allowed:
            raise LeadNotAuthorised(auth.reason)
        self._lead_auth = auth
        try:
            yield auth
        finally:
            self._lead_auth = None

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
    # Confirmed live: these false-positived on the bare "email" word before the
    # (?<!with[ _]) exclusion was added to BLOCK-LEAD-EMAIL — a sign-in method
    # selector, not a lead-contact action.
    ("text", "Continue with Email"),
    ("resource_id", "com.bayut.app:id/fl_continue_with_email"),
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


# Production-only: must be blocked on prod, tappable on staging.
_MUST_BLOCK_IN_PRODUCTION: tuple[tuple[str, str], ...] = (
    ("text", "Sign Up"),
    ("text", "Create an account"),
    ("text", "Save this search"),
    ("text", "Alert Me of New Properties"),
    ("text", "Add to Favourites"),
    ("content_desc", "Save property"),
    ("resource_id", "com.bayut.app:id/btn_favourite"),
    ("text", "Generate Report"),
    ("text", "Download Report"),
    ("text", "Confirm Details"),
    ("text", "Add to Portfolio"),
    ("text", "Claim Transaction"),
    ("text", "Submit Claim"),
    ("text", "Sell My Property"),
    ("text", "BayutGPT"),
    ("text", "Edit Profile"),
    ("text", "Share Report"),
)

# Read-only destinations that share vocabulary with the write actions above. These must
# stay reachable even on production, or the crawl cannot map half the app.
_MUST_NOT_BLOCK_IN_PRODUCTION: tuple[tuple[str, str], ...] = (
    ("content_desc", "Favourites"),
    ("resource_id", "com.bayut.app:id/nav_favourites"),
    ("text", "Saved Searches"),
    ("text", "Portfolio"),
    ("text", "My TruEstimate Reports"),
    ("text", "Activity Log"),
    ("text", "Dubai Transactions"),
)


def _run_environment_selftest(verbose: bool) -> list[str]:
    """Production blocks writes; staging does not; navigation survives both."""
    failures: list[str] = []
    prod = SafetyPolicy(app_package="com.bayut.app", environment="production")
    stage = SafetyPolicy(app_package="com.bayut.app", environment="staging")

    for field_name, value in _MUST_BLOCK_IN_PRODUCTION:
        d = prod.evaluate(_synthetic(field_name, value))
        if d.verdict != "BLOCK":
            failures.append(f"PROD NOT BLOCKED: {field_name}={value!r} -> {d.verdict}")
        elif verbose:
            print(f"  PROD BLOCK   {value!r:<34} {d.rule_id}")
        # The same control must be reachable on staging, unless a base rule covers it.
        s = stage.evaluate(_synthetic(field_name, value))
        if s.verdict == "BLOCK" and str(s.rule_id).startswith("PROD-"):
            failures.append(f"STAGING WRONGLY BLOCKED BY PROD RULE: {value!r} -> {s.rule_id}")

    for field_name, value in _MUST_NOT_BLOCK_IN_PRODUCTION:
        d = prod.evaluate(_synthetic(field_name, value))
        if d.verdict == "BLOCK":
            failures.append(
                f"PROD OVER-BLOCKED navigation: {field_name}={value!r} -> {d.rule_id}")
        elif verbose:
            print(f"  PROD {d.verdict:<8} {value!r:<34} {d.rule_id or '-'}")

    if prod.environment != DEFAULT_ENVIRONMENT or DEFAULT_ENVIRONMENT != "production":
        failures.append("DEFAULT_ENVIRONMENT is not 'production'")
    if SafetyPolicy().environment != "production":
        failures.append("a bare SafetyPolicy() does not default to production")
    return failures


def _run_lead_selftest(verbose: bool) -> list[str]:
    """Lead controls open only when an allowlisted agency is proven on screen."""
    failures: list[str] = []
    policy = SafetyPolicy(app_package="com.bayut.app")
    call = _synthetic("content_desc", "Call agent")

    # 1. Blocked by default.
    if policy.evaluate(call).verdict != "BLOCK":
        failures.append("lead CTA not blocked outside a lead test")

    # 2. Refused when the agency is not on screen.
    wrong = [_synthetic("text", "Marina Heights Real Estate"), call]
    if policy.authorise_lead(wrong).allowed:
        failures.append("lead authorised for a non-allowlisted agency")
    try:
        with policy.lead_test(wrong):
            failures.append("lead_test did not raise for a non-allowlisted agency")
    except LeadNotAuthorised:
        pass

    # 3. Allowed when the allowlisted agency IS on screen.
    right = [_synthetic("text", "Explorer Real Estate"), call]
    auth = policy.authorise_lead(right)
    if not auth.allowed or auth.agency_seen != "Explorer Real Estate":
        failures.append("lead not authorised despite Explorer Real Estate on screen")
    with policy.lead_test(right):
        d = policy.evaluate(call)
        if d.verdict != "ALLOW":
            failures.append(f"lead CTA still blocked inside an authorised lead test: {d.rule_id}")
        # 4. The exemption is narrow: non-lead rules stay in force inside the block.
        for value in ("Delete Account", "Log out", "Report this listing", "Sign Up"):
            if policy.evaluate(_synthetic("text", value)).verdict != "BLOCK":
                failures.append(f"lead_test wrongly exempted {value!r}")
        if verbose:
            print(f"  LEAD ALLOW   {'Call agent':<34} inside authorised lead test")

    # 5. The exemption does not leak past the block.
    if policy.evaluate(call).verdict != "BLOCK":
        failures.append("lead exemption leaked after the lead_test block exited")
    if policy._lead_auth is not None:
        failures.append("lead authorisation not cleared after the block")
    return failures


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

    env_failures = _run_environment_selftest(verbose)
    lead_failures = _run_lead_selftest(verbose)
    failures.extend(env_failures)
    failures.extend(lead_failures)

    total = (len(_MUST_BLOCK) + len(_MUST_NOT_BLOCK) + 1
             + len(_MUST_BLOCK_IN_PRODUCTION) * 2 + len(_MUST_NOT_BLOCK_IN_PRODUCTION) + 2
             + 9)  # lead-authorisation assertions
    print(f"\nselftest: {total - len(failures)}/{total} assertions passed")
    print(f"  default environment : {DEFAULT_ENVIRONMENT}")
    print(f"  lead allowlist      : {list(LEAD_TEST_AGENCIES)}")
    for f in failures:
        print(f"  FAIL  {f}")
    if failures:
        print("\nDO NOT CRAWL until these pass.")
        return 1
    print("Blocklist, production guard and lead gate behave as specified. Safe to crawl.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_selftest(args: argparse.Namespace) -> int:
    return run_selftest(verbose=args.verbose)


def _cmd_rules(args: argparse.Namespace) -> int:
    policy = SafetyPolicy.load(args.config, app_package=args.app_package,
                               environment=args.environment)
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
    policy = SafetyPolicy.load(args.config, app_package=args.app_package,
                               permissive=args.allow_uncertain_taps,
                               environment=args.environment)
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
        print(f"environment : {policy.environment.upper()}")
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
    policy = SafetyPolicy.load(args.config, app_package=args.app_package,
                               environment=args.environment)
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
    p.add_argument("--environment", choices=["production", "staging"],
                   default=os.environ.get("TEST_ENVIRONMENT", DEFAULT_ENVIRONMENT),
                   help="PRODUCTION by default and until told otherwise. Production adds "
                        "the data-creation blocklist.")
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
