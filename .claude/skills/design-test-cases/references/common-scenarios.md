# Mandatory cross-cutting scenarios

Every feature suite includes these unless the scenario genuinely does not apply. They go at the end of the suite, after the feature-specific cases.

**These are patterns, not text to paste.** Each entry gives the intent and a worked example from a real suite. Rewrite the example so it names the actual surface, component, and behaviour of the feature you are testing. A pasted generic case is worse than no case, because it looks like coverage and provides none.

**The specifics come from the app knowledge base, not from here.** Languages, device lists, minimum OS versions, deeplink domains, and analytics conventions differ per app — read them from `apps/<app>.md`, read in full in Phase 0. Where a needed value is `TODO` in the knowledge base, ask rather than guessing; a localisation case naming the wrong languages is worse than an honest gap.

The examples below use Bayut UAE values because that is the knowledge base with real evidence behind it. Substitute the target app's values.

If you drop a scenario, say which and why in the Phase 7 output.

---

## 1. Localisation — every language in the app knowledge base

Cover the app's full language set. This differs per app: Bayut UAE ships EN/AR/ZH/RU, while other apps in the group ship smaller or different sets.

**RTL is a layout test, not a translation test.** Any RTL language in the knowledge base — Arabic on the MENA apps, Urdu on the Pakistan apps — needs mirrored alignment, correct icon and chevron direction, and correct sheet and drawer slide direction verified separately from whether the words are right.

Note which languages run long and which run short. Long strings (Russian) cause truncation and overlap; short strings (Chinese) cause gaps and centring problems.

> Verify the survey is localized correctly in English (EN), Arabic (AR), Chinese (ZH), and Russian (RU).

Where a localisation sheet is supplied, write a separate case asserting no truncation or overlap in the longest strings.

## 2. Deeplinks and entry points

Every route into the feature's surface, using the domain, localised path pattern, and entry-point list from the app knowledge base. Where deeplinks apply, test them in three app states: fresh install, killed/closed, and running in background. Include the localised deeplink variants for each language in the knowledge base where the surface has them.

> Verify the survey is displayed correctly when the DPV is opened from all supported entry points (e.g., Deeplink, Remarketing) after a qualifying lead generation.

## 3. Offline and slow network

Three distinct cases, not one: behaviour under slow network, behaviour with no connection, and behaviour across a transition. The transition case is the one that finds bugs — stuck spinners, duplicate submissions, duplicate analytics events.

> Verify the survey behaves correctly under slow network conditions.

> Verify an appropriate error message is displayed and the survey is not submitted when there is no internet connection at the time of submission.

> Verify the survey handles network transitions (Online → Offline → Online) and Airplane Mode toggle during submission without displaying a stuck UI or triggering duplicate analytics events.

## 4. Foldable and mini-screen Android

Use the device list from the app knowledge base. Foldables need both folded and unfolded states, and the fold transition while the feature is on screen. Mini screens are the layout-overflow risk.

> Verify the survey UI/layout is displayed correctly on foldable and mini-screen Android devices.

## 5. iPad and mini-screen iOS

Use the device list from the app knowledge base. iPad needs the larger layout and, where the app supports it, Split View and Slide Over. Mini-screen iOS is where bottom sheets overflow and keyboards cover controls.

> Verify the survey UI/layout is displayed correctly on iPad and mini-screen iOS devices.

## 6. Figma UI parity

Against the approved design: spacing, typography, colours, iconography, and component states including pressed, disabled, loading, and error. Also transitions — sheets sliding in and out.

> Verify the survey bottom sheet matches the approved UI/UX design.

Name the Figma frame in Notes when a link is supplied.

## 7. Firebase / GA4 analytics events

Assert event names, parameter names, and parameter values against the tracking sheet. Two things to always check beyond the happy path: that no duplicate events fire on repeated or rapid interaction, and that parameter values are correct when they are derived from persisted state rather than the current screen.

> Verify the survey analytics event is fired with the correct event name, parameters, and values according to the tracking sheet.

Check the app knowledge base for platform-specific analytics constraints. On the GA4 apps, event-scoped custom dimension values are capped at 100 characters and truncate silently above that — where a feature sends free text to GA, write a case at the boundary.

## 8. Old OS compatibility — both platforms

Smoke the feature on the oldest supported iOS and Android versions. Rendering differences and crashes on older WebViews and older system fonts are the usual finds.

> Verify backward compatibility by performing smoke testing on older OS versions (e.g., Android 8 / iOS 13) to ensure the feature works without crashes.

Take the version numbers from the app knowledge base. If the knowledge base marks them `TODO`, ask — naming a wrong OS floor sends a tester to a device that proves nothing.

## 9. Both platforms

Everything above is verified on iOS and Android independently. Where behaviour is expected to differ by platform, that difference is itself a test case rather than something to gloss over.

---

## Situational additions

Not mandatory, but consider them:

- **App lifecycle** — kill and relaunch, background and foreground, fresh install. Mandatory whenever the feature persists any state.
- **Auth transitions** — logout and login, session expiry. Mandatory whenever behaviour is per-user.
- **Remote config runtime toggle** — flipping the flag while the app is running. Mandatory whenever the feature is flag-gated.
- **Accessibility** — dynamic type, VoiceOver and TalkBack. Add where the feature has meaningful interactive controls.
- **Interrupts** — incoming call, notification, or system dialog while the feature is on screen.
