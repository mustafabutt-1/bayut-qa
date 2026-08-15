# OLX PK

**Status:** Stub — needs filling
**Platforms:** iOS, Android (native)
**Testmo project ID:** TODO

> This is a **knowledge base**, not just a config file. It is read in full before any test suite is designed for this app, so everything a designer needs to write cases that feel native to this app belongs here: how the app is structured, what its critical flows are, where it has broken before, and the vocabulary its team uses.
>
> Keep it app-specific. The nine universal cross-cutting scenarios (localisation, deeplinks, offline, foldable/iPad, Figma parity, analytics, old OS, both platforms) live in `../common-scenarios.md` and must **not** be duplicated here. This file captures only what is true of *this app* and not the others.
>
> Never invent a value. Unknown facts stay marked `TODO` until someone who knows fills them in — a confidently wrong entry here silently corrupts every suite designed for this app.

---

## A. Configuration

| Setting | Value |
| --- | --- |
| Testmo project ID | TODO |
| Case template | TODO — inherit from `../testmo-mapping.md` unless this app differs |
| Primary market(s) | Pakistan |
| Bundle IDs (iOS / Android) | TODO |

### Languages

| Code | Language | RTL | Notes |
| --- | --- | --- | --- |
| TODO | | | |

Unconfirmed starting point: likely EN + Urdu. **Urdu is RTL.** Confirm the full set.

Mark RTL explicitly — RTL is a **layout** test, not just a translation test. Note which languages run long (truncation risk) and which run short (gap and centring risk).

### Device matrix

| Platform | Devices |
| --- | --- |
| iOS | TODO — name the specific iPad, mini-screen, and low-end devices the team keeps |
| Android | TODO — foldable, mini-screen, low-end |

### Minimum supported OS

TODO — iOS and Android. Confirm rather than assume; this changes at least annually.

### Analytics

Platform: TODO (GA4 / Firebase / other)
Tracking sheet location: TODO
Known constraints: TODO (e.g. GA4 custom-dimension 100-char cap)

### Remote config

Platform: TODO
Flag naming convention: TODO

---

## B. Vocabulary

Use the team's own terms in test cases. A tester reading "property detail view" when the team says DPV will hesitate.

| Term | Meaning |
| --- | --- |
| TODO | |

---

## C. Product domain

*What this app actually is — the context a designer needs to know what matters.*

- **Vertical(s):** General classifieds (motors, property, electronics, jobs, goods) — ads rather than properties.
- **Core value exchange:** TODO — what is a "lead" / conversion here (a call, a WhatsApp, a chat message, an offer)?
- **Who posts and who consumes:** TODO — agents vs private sellers, buyers vs browsers.
- **Anything structurally unusual:** TODO

**Note for whoever fills this in:** Classifieds vocabulary — ads, not properties. Capture the actual terms. Confirm domain and localised path pattern.

---

## D. Key flows and surfaces

*The screens and journeys test cases touch most. Give each surface its team name and its entry points.*

| Surface | Team term | Entry points |
| --- | --- | --- |
| TODO | | |

Note any flow where a trigger and its effect are separated across screens, sessions, or time — those are the ones that breed the hardest bugs and deserve explicit call-outs.

---

## E. Regression-critical areas

*Distilled from the app's regression checklist. The areas that must be re-verified on any change, the fragile parts, and the parts with a history of defect leakage.*

Do not paste the whole checklist. Distil it into the areas and the reason each matters, so a designer knows **what to protect** when a feature touches nearby code. One line each.

- TODO

---

## F. App-specific edge cases and gotchas

*Hard-won knowledge. Platform quirks, integration seams, and the bugs that have bitten this app before.*

- **Integrations:** TODO — chat, payments, MoEngage, maps, third-party SDKs and their known quirks.
- **Platform splits:** TODO — where iOS and Android genuinely diverge in this app.
- **Historical leakage:** TODO — categories of bug that have escaped to production before.

---

## G. App-specific learnings

*Growing log, fed by the `update-knowledge` skill. App-scoped rules only; group-wide rules live in `../learnings.md`.*

*(none yet)*
