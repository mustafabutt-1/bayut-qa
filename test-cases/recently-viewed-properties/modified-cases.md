# Recently Viewed Properties — Changed Test Cases

Tracks every case touched during the Testmo review cycle so far, against the 79-case finalized baseline. Case numbers below are the **original numbering** from that baseline (stable reference point across edits), not the working file's current row order, which has grown as new cases were inserted.

Source of truth is `final_cases.json` (not checked into this repo — see `_context.md`). No CSV has been re-exported since review comments started; this file **is** the current state, generated directly from that JSON.

---

## Modified cases

### 1. Verify the Recently Viewed Properties carousel is displayed on the homepage in the correct position for users in the `recently_viewed_variant` experiment group.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property on the DPV
When the user navigates to the homepage
And the user scrolls down past the Homepage banners carousel
Then the section headed "Recently Viewed Properties" is displayed on the homepage
And the section is rendered directly below the Homepage banners carousel
And the section is rendered directly above the "Recommended Properties for You" carousel
```

**Expected Result**

1. A section headed "Recently Viewed Properties" is visible on the homepage.
2. The section sits directly below the Homepage banners carousel, with no other module in between.
3. The section sits directly above the "Recommended Properties for You" carousel.

**Notes:** Placement per PRD 'Change Required' and Figma frames 2847-1833 / 2847-3352. "Homepage banners" is the team term for the rotating promotional widget at the top of the homepage (TruEstimate, Portfolio, Dubai Transactions, Propco, etc.) -- renamed from "promotional banner carousel" per QA terminology correction.

---

### 2. Verify the Recently Viewed Properties carousel is not displayed on the homepage for users in the `recently_viewed_control` experiment group.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_control` experiment group
And the user has viewed at least 1 property on the DPV
And GA DebugView is attached to the device
When the user navigates to the homepage and scrolls the full length of the homepage
And the user opens the More screen, navigates to Activity Log, and scrolls to "Viewed Properties"
Then no "Recently Viewed Properties" section is displayed at any scroll position on the homepage
And the "Recommended Properties for You" carousel is displayed directly below the Homepage banners carousel
And no `recently_viewed_carousel_impression` event is fired
And the "Viewed Properties" section is displayed in Activity Log with the user's viewing history, most recent first
```

**Expected Result**

1. No section headed "Recently Viewed Properties" appears anywhere on the homepage.
2. "Recommended Properties for You" renders directly below the Homepage banners carousel, as in the pre-feature build.
3. No `recently_viewed_carousel_impression` event appears in GA DebugView.
4. The "Viewed Properties" section is displayed in Activity Log with the user's viewing history, most recent first -- confirming control users are scoped away from Home only, not blocked from viewing history entirely.

**Notes:** Remote Config key `recently_viewed_carousel_homepage` resolves to `recently_viewed_control`. Confirmed spec: control = Recently Viewed Properties absent on Home, Viewed Properties present in Activity Log only. Per Testmo review (H Mobile Apps, 2026-08-13) this case is extended to verify both halves of that definition in one place, mirroring the same fix applied to case 3.

---

### 3. Verify the Viewed Properties section in Activity Log (More screen) remains available for users in the `recently_viewed_control` experiment group.

**Description**
```gherkin
Given the Remote Config key `recently_viewed_carousel_homepage` resolves to `recently_viewed_control` for the test user
And the user has viewed at least 1 property
When the user navigates to the homepage and scrolls the full length of the page
And the user opens the More screen and navigates to Activity Log
And the user scrolls to the "Viewed Properties" section
Then no "Recently Viewed Properties" section is displayed anywhere on the homepage
And the "Viewed Properties" section is displayed in Activity Log
And the listings shown match the user's viewing history in most-recent-first order
```

**Expected Result**

1. No "Recently Viewed Properties" section appears anywhere on the homepage for the control group.
2. The "Viewed Properties" section is displayed in Activity Log under the More screen for the control group.
3. The listings match the user's viewing history, ordered most recent first.

**Notes:** Per the confirmed Remote Config values, control sees Viewed Properties only in Activity Log, never on Home. Per Testmo review comment (B Mobile Apps, 2026-08-13): case now verifies both halves of control-arm scoping in one place -- absent on Home, present only in Activity Log -- rather than relying on case 2 to cover the Home-absence half separately.

---

### 4. Verify the Recently Viewed listings are displayed on both the Home carousel and the Viewed Properties section of Activity Log for users in the `recently_viewed_variant` experiment group.

**Description**
```gherkin
Given the Remote Config key `recently_viewed_carousel_homepage` resolves to `recently_viewed_variant` for the test user
And the user has viewed exactly 3 distinct properties
When the user opens the homepage and records the carousel contents and order
And the user opens the More screen, navigates to Activity Log, and scrolls to "Viewed Properties"
Then the homepage carousel and the Activity Log "Viewed Properties" section show the same set of listings
And both surfaces order the listings most recent first
```

**Expected Result**

1. Both surfaces contain the same 3 listings, with no listing present in one and missing from the other.
2. The order of listings is identical on both surfaces, most recently viewed first.

**Notes:** Per the confirmed Remote Config values, variant sees the carousel on both Home and Activity Log. Per Testmo review comments (B Mobile Apps, 2026-08-13): title no longer calls Activity Log's section a carousel; count changed from 5 to 3 per reviewer's stated activation count. [OPEN QUESTION -- see conversation] this reviewer says the Home carousel activates at 3 views, which conflicts with an earlier reviewer comment on case 1 stating there is no 3-view condition and the section shows after 1 view. Cases 1, 2, 3, 5, 6, 7, 9, 10, 49, 56, 57, 68, 72 all encode the "1 view" reading and may need to revert to "3" once this is resolved -- not changed yet, pending confirmation.

---

### 6. Verify the Recently Viewed carousel responds correctly when `recently_viewed_carousel_homepage` changes value while the app is running.

**Description**
```gherkin
Given the Remote Config key `recently_viewed_carousel_homepage` resolves to `recently_viewed_control` for the test user
And the user has viewed at least 1 property
And the app is running on the homepage with no "Recently Viewed Properties" section shown
When the key is republished with the value `recently_viewed_variant`
And the user backgrounds the app past the configured minimum fetch interval and returns to the homepage
Then the "Recently Viewed Properties" section is displayed on the homepage
And the carousel renders the viewing history in most-recent-first order
And the "Viewed Properties" section in Activity Log is unaffected throughout, showing the same history before and after the change
And the app does not crash and the homepage does not render a duplicate or half-built section
```

**Expected Result**

1. The section appears on the homepage once the new config value has been fetched and activated.
2. The carousel shows the previously viewed listings, most recent first.
3. Activity Log's "Viewed Properties" section shows the same listings before and after the config change, confirming this key affects Home visibility only.
4. No crash, duplicated section, or partially rendered carousel occurs during the config change.

**Notes:** Flag toggling while the app runs is a mandatory remote config scenario for Bayut UAE. Production fetch interval caching applies — confirm the debug interval with dev.

---

### 7. Verify the Recently Viewed carousel falls back safely when `recently_viewed_carousel_homepage` holds a value outside the three defined values.

**Description**
```gherkin
Given the test user has viewed at least 1 property
When `recently_viewed_carousel_homepage` is published with an unexpected value such as "test123", not one of the three defined values, and the app is relaunched
Then the app does not crash
And the homepage does not display the "Recently Viewed Properties" section
And the homepage renders all other modules normally
And the "Viewed Properties" section in Activity Log is still displayed with the user's history
```

**Expected Result**

1. The app remains stable with no crash on launch or on the homepage.
2. No "Recently Viewed Properties" section, empty carousel, or orphaned header is shown on the homepage for the unrecognised value.
3. Banners, "Recommended Properties for You" and all other homepage modules render in their normal order.
4. Activity Log's "Viewed Properties" section still shows the user's history, unaffected by the unrecognised value.

**Notes:** The key resolving to a missing/absent state is already covered as the defined `null` case above; this case is scoped to a genuinely unrecognised string value, which is undefined behaviour — confirm the intended fallback with dev before execution.

---

### 10. Verify the Recently Viewed card uses the same listing card design as the Recommended Properties for You card.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property on the DPV
When the user opens the homepage with both carousels visible on screen
And the user compares a Recently Viewed card against a "Recommended Properties for You" card
Then both cards use the same width, height, corner radius, image aspect ratio and internal spacing
And both cards present price, bed count, area and location in the same order and typography
And both cards place the TruCheck badge at the top-left and the favourite heart at the top-right of the image
```

**Expected Result**

1. The two cards are visually identical in dimensions, corner radius, image aspect ratio and internal padding.
2. Price, bed count, area and location appear in the same sequence with the same font size, weight and colour on both cards.
3. The TruCheck badge sits at the top-left and the favourite heart at the top-right of the image on both cards.

**Notes:** PRD: 'Maintain the existing listing card design used across homepage recommendation modules.'

---

### 49. Verify the homepage stays scrollable and the Recently Viewed carousel renders the correct listings once loading completes under a throttled network.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property
And the device network is throttled to a slow 3G profile
When the user opens the homepage and waits for it to finish loading
Then the homepage remains scrollable while the section is loading
And the carousel eventually renders the correct listings in most-recent-first order
And no loading placeholder or spinner remains once the homepage has finished loading
```

**Expected Result**

1. The homepage can be scrolled vertically while the Recently Viewed section is still loading.
2. The carousel renders with the correct listings in most-recent-first order once loading completes.
3. No skeleton, placeholder card, or spinner is visible in the section after the homepage has loaded.

---

### 54. Verify the Recently Viewed section is hidden when every listing in the history has become unavailable.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And every listing in the user's Recently Viewed history has since been deactivated
When the user opens the homepage
And the user scrolls the full length of the homepage
Then no "Recently Viewed Properties" section header is displayed
And no empty carousel, placeholder card, or blank vertical space is rendered in its place
And the "Recommended Properties for You" carousel renders directly below the Homepage banners carousel
```

**Expected Result**

1. The section header "Recently Viewed Properties" is not present anywhere on the homepage.
2. No empty carousel row, placeholder card, or vertical gap is visible where the section would sit.
3. "Recommended Properties for You" sits directly below the Homepage banners carousel.

**Notes:** Filtering unavailable listings can empty the section — it must then follow the PRD's no-history rule and hide completely.

---

### 63. Verify the Recommended Properties for You carousel is unchanged by the introduction of the Recently Viewed section.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed section is displayed above the "Recommended Properties for You" carousel
And GA DebugView is attached to the device
When the user scrolls, swipes, taps a card and toggles a favourite in the "Recommended Properties for You" carousel
Then the carousel renders the same number of cards with the same card design as in the pre-feature build
And horizontal scrolling, card taps and favourite toggles behave as in the pre-feature build
And its existing analytics events fire unchanged
```

**Expected Result**

1. The Recommended Properties carousel shows the same card count and identical card layout as the pre-feature build.
2. Swiping, tapping a card and toggling a favourite produce the same results as in the pre-feature build.
3. The carousel's existing GA4 events fire with unchanged names and parameter values.

---

### 64. Verify the Homepage banners are unchanged by the introduction of the Recently Viewed section.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the homepage is displayed with the Homepage banners carousel above the Recently Viewed section
When the user allows the banner carousel to auto-rotate through all banners
And the user taps each banner in turn
Then the Homepage banners carousel auto-rotates and its pagination dots update as in the pre-feature build
And each banner opens its existing destination screen
```

**Expected Result**

1. The banners rotate at the same interval and the pagination dots advance in step, as in the pre-feature build.
2. Each banner opens the same destination it opened before the feature was added.

**Notes:** Homepage banners include TruBroker, TruEstimate, Portfolio, Dubai Transactions and Propco entry points per the Figma frames.

---

### 56. Verify `recently_viewed_carousel_impression` is fired when the Recently Viewed carousel is scrolled into view on the homepage.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property
And GA DebugView is attached to the device
When the user lands on the homepage and scrolls until the Recently Viewed carousel is fully visible
Then `recently_viewed_carousel_impression` is fired once
And it carries `page_type = home`, `website_section = property` and `experiment_group = recently_viewed_variant`
```

**Expected Result**

1. GA DebugView shows exactly one `recently_viewed_carousel_impression` event when the carousel becomes visible.
2. The event carries `page_type = home`, `website_section = property` and `experiment_group = recently_viewed_variant`.

---

### 57. Verify `recently_viewed_carousel_impression` is not fired when the carousel is never scrolled into view.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property
And GA DebugView is attached to the device
When the user lands on the homepage and navigates away without scrolling down to the carousel
Then no `recently_viewed_carousel_impression` event is fired
And `recently_viewed_carousel_test` is still fired once for the homepage landing
```

**Expected Result**

1. No `recently_viewed_carousel_impression` event appears in GA DebugView for that homepage visit.
2. Exactly one `recently_viewed_carousel_test` event is present for the homepage landing.

**Notes:** [ASSUMED — needs verification] the impression is viewability-based rather than render-based. Confirm the trigger definition with product.

---

### 68. Verify the Recently Viewed Properties section is localised correctly in English (EN), Arabic (AR), Chinese (ZH) and Russian (RU).

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property
When the user switches the app language to English, Arabic, Chinese and Russian in turn
And the user returns to the homepage and scrolls to the Recently Viewed section in each language
Then the section header is correctly translated in each language, matching the Bayut App Copy Requirements sheet
And the price, beds, area and location fields render in the selected language in each case
And no untranslated English string remains in the section in AR, ZH or RU
```

**Expected Result**

1. The section header text in each language matches the approved string in the Bayut App Copy Requirements sheet; in English it reads "Recently Viewed Properties".
2. Card price, bed count, area unit and location render in the selected language, including localised numerals and units where applicable.
3. No English string is left in the section when the app is in Arabic, Chinese or Russian.

**Notes:** All four languages are mandatory for Bayut UAE.

---

### 70. Verify the Recently Viewed section handles the app's long-running and short-running language strings without truncation, overlap, or misalignment.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed carousel contains listings with long location names
When the user views the section in the app's long-running language
And the user views the section in the app's short-running language
Then in the long-running language the section header and card fields are not truncated mid-word and do not overlap adjacent elements
And in the short-running language the section header and card fields are aligned to the same margins as in English with no unexpected gaps
```

**Expected Result**

1. In the long-running language, the header renders fully or truncates cleanly with an ellipsis, and no card text overlaps the badge, heart or card border.
2. In the short-running language, the header and card fields align to the same leading margin as English, with no centring shift or empty gaps in the card body.

**Notes:** Generic by design: the assertion targets the long-string/short-string characteristic, not Russian/Chinese specifically, so it stays valid if the app's language set changes. Per the app knowledge base (Section A), the current long-running language is Russian and the current short-running language is Chinese -- execute this case against those two today.

---

### 72. Verify the localised deeplink prefixes /ar/, /zh/ and /ru/ land on the homepage with the Recently Viewed section rendered in the matching language.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 1 property
When the user opens the bayut.com deeplink with the /ar/ prefix, then the /zh/ prefix, then the /ru/ prefix, in separate sessions
And the user scrolls to the Recently Viewed section on each occasion
Then the homepage opens in the language matching the deeplink prefix
And the Recently Viewed section header and card fields are rendered in that same language
```

**Expected Result**

1. Each localised deeplink opens the homepage in its matching language (AR, ZH, RU respectively).
2. The Recently Viewed section header and card fields (price, beds, area, location) are translated to match, with no residual English string.

**Notes:** Localised deeplink prefixes per knowledge base Section D. Split from the entry-point matrix case above because this asserts language correctness, a different failure mode from routing correctness.

---

### 77. Verify the Recently Viewed Properties section matches the approved UI/UX design.

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed carousel is displayed on the homepage
When the user inspects the section header, spacing, card styling, and header controls
Then the section header reads exactly "Recently Viewed Properties" in the specified typeface, weight, size and colour
And the spacing above the header, between the header and the cards, and below the carousel matches the design
And the card image aspect ratio, corner radius, badge pill styling, and favourite heart size and colour match the design
And no additional control such as a "View All" link is present in the section header
```

**Expected Result**

1. The header string, typeface, weight, size and colour are pixel-consistent with the Figma frames.
2. The vertical spacing above the header, between header and cards, and below the carousel matches the design measurements.
3. Card corner radius, image aspect ratio, badge pill shape and text, and heart icon size and fill colour match the design.
4. The section header contains only the title, with no "View All" or chevron control.

**Notes:** Figma frames 2847-1833 and 2847-3352. Figma MCP access was unavailable; parity assertions are based on the two supplied frame screenshots. Re-verify against the live file at execution. Simplified per Testmo review (H Mobile Apps, 2026-08-13) -- dropped the literal "open Figma / compare against Figma" steps as redundant procedural detail; the frame citation now lives here instead of in the Given/When, matching how every other case in this suite cites Figma.

---

## Notes-only changes

Title, Description and Expected Result unchanged — only Notes updated.

### 5. Verify users for whom `recently_viewed_carousel_homepage` resolves to null do not see the Home carousel but still see Viewed Properties in Activity Log.

**Notes:** Confirmed by product: null behaves identically to recently_viewed_control — hidden on Home, shown in Activity Log. Coverage rationale: variant / control / null are the three defined resolution states for this key (see case 7's fallback note); each is a distinct code path and gets its own case rather than being inferred from the others.

### 14. Verify all listing badge types render on Recently Viewed cards consistently with other homepage carousels.

**Notes:** [ASSUMED — needs verification] Badge and package values per the Parameter Definitions sheet (`property_badge`, `package_type`); the specific list (Verified, Premium, Hot, Superhot) beyond TruCheck is not independently confirmed in this pass — verify the live enum against the Parameter Definitions sheet or Figma before executing.

### 67. Verify Firebase Crashlytics shows no new fatal or non-fatal issues attributable to the Recently Viewed carousel.

**Notes:** Sign-off gate

---

## New cases added

### Verify a listing is excluded from the Recently Viewed carousel once the user has contacted it.

**Section:** 8. Empty, Error & Network States

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has viewed at least 2 listings, both present in the Recently Viewed carousel
When the user opens one of those listings' DPV and generates a lead via **Call**
And the user navigates back to the homepage
Then the contacted listing is no longer present in the Recently Viewed carousel
And the other previously viewed listing is still present, unaffected
```

**Expected Result**

1. The contacted listing does not appear on any card in the Recently Viewed carousel after the lead is generated.
2. The other previously viewed listing remains present in the carousel, in its previous relative order.

**Notes:** Requirement surfaced via Testmo review comment (B Mobile Apps, 2026-08-13): a contacted listing must not appear in Recently Viewed. [ASSUMED — needs verification] this case tests exclusion via a Phone lead as the representative contact channel, and assumes the exclusion is permanent rather than temporary or reversed by re-viewing the listing after contact — none of that mechanics is specified in the comment. Confirm with product/QA before executing: (a) does every lead channel (Email/WhatsApp/SMS), not just Call, trigger exclusion, and (b) if the user views the same listing again after contacting it, does it re-enter the carousel or stay excluded.

---

### Verify the Recently Viewed card's listing image renders at full resolution without blur, pixelation, or upscaling artefacts.

**Section:** 2. Listing Card Content & Parity

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed carousel is displayed with at least 3 listings, each with a listing image
When the user inspects each card's image at the device's native screen density
Then each image renders sharply with no visible blur, pixelation, or stretching
And each image's dimensions, aspect ratio and position behind the badge and favourite heart overlays match the "Recommended Properties for You" card exactly
```

**Expected Result**

1. No card image shows visible blur, pixelation, or upscaling artefacts at native device density.
2. Image dimensions, aspect ratio, and position relative to the badge/heart overlays are identical to the "Recommended Properties for You" card, matching the parity already established in case 10.

**Notes:** [ASSUMED — needs verification] no confirmed source/target resolution values or image-loading library are in the knowledge base -- this checks observable sharpness and parity rather than asserting specific pixel dimensions. Requested via Testmo review (B Mobile Apps, 2026-08-13).

---

### Verify a listing without an image shows the fallback placeholder image on its Recently Viewed card.

**Section:** 2. Listing Card Content & Parity

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the user has identified an image-less listing by sorting LPV results by Newest/Latest and opening one with no listing image
When the user views that listing's DPV and returns to the homepage
Then that listing's card in the Recently Viewed carousel shows the app's standard fallback placeholder image, not a blank or broken image area
And the card's other fields render normally around the placeholder
```

**Expected Result**

1. The card displays the standard fallback placeholder image where the listing image would be, with no blank space or broken-image icon.
2. Price, bed count, area, location, and any badges render in their normal positions, unaffected by the missing image.

**Notes:** [ASSUMED — needs verification] the exact fallback asset/placeholder design is not confirmed against Figma or the app knowledge base -- this asserts a placeholder appears and other fields are unaffected, without asserting a specific icon or copy. Setup method per Testmo review comment (B Mobile Apps, 2026-08-13): sort LPV by Newest/Latest to find an image-less listing to seed the viewing history.

---

### Verify the Recently Viewed carousel's scroll-release behaviour (snap vs. free) at card boundaries and at the ends of the rail.

**Section:** 4. Interaction & Navigation

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed carousel contains at least 6 listings
When the user drags the carousel partway between two cards and releases
And the user drags the carousel past its first and last card and releases
Then a partial-drag release settles the carousel on the nearest card boundary rather than resting mid-card
And an over-drag past either end shows the same over-scroll effect as the "Recommended Properties for You" carousel, then springs back to the boundary card
```

**Expected Result**

1. Releasing a partial drag mid-carousel settles on the nearest card boundary; the carousel never rests with a card half-visible.
2. Dragging past the first or last card shows the same over-scroll/rubber-band effect as the "Recommended Properties for You" carousel, and releases back to the boundary card.

**Notes:** [ASSUMED — needs verification] whether the rail is genuinely snap-to-card or free-scroll is not confirmed against Figma/implementation -- written to observe and report whichever behaviour is actually present, compared against the Recommended Properties carousel as the reference. Requested via Testmo review (B Mobile Apps, 2026-08-13); overlaps but is distinct from case 28, which covers peek visibility and general over-scroll damping -- this one specifically targets snap-vs-free release behaviour.

---

### Verify each Recently Viewed card shows a shimmer placeholder while its content is loading.

**Section:** 8. Empty, Error & Network States

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the device network is throttled to a slow 3G profile
When the user opens the homepage and the Recently Viewed section begins loading
Then each card position shows a shimmer/skeleton placeholder in place of the image and text fields
And the shimmer is replaced by the real card content once loading completes, with no blank frame in between
```

**Expected Result**

1. While loading, each card position shows a shimmer/skeleton animation rather than a blank space.
2. The shimmer is replaced directly by loaded card content, with no intermediate blank frame.

**Notes:** [ASSUMED — needs verification] exact shimmer duration/animation is not confirmed against Figma. Overlaps case 49 (slow-network section loading) but targets the per-card shimmer visual specifically, not the section-level loading state case 49 covers. Requested via Testmo review (B Mobile Apps, 2026-08-13).

---

### Verify a Recently Viewed card shows a press/tap visual effect when pressed.

**Section:** 4. Interaction & Navigation

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed carousel is displayed
When the user presses and holds a card briefly before releasing
Then the card shows a visible press effect (ripple, dim, or highlight) while held
And the effect matches the press feedback shown on a "Recommended Properties for You" card
```

**Expected Result**

1. Pressing a card shows a visible ripple/highlight/dim effect while held, matching the standard press feedback used elsewhere in the app.
2. The press effect is visually identical to the one shown when pressing a "Recommended Properties for You" card.

**Notes:** [ASSUMED — needs verification] exact press-effect styling (ripple colour, dim opacity) is not confirmed against Figma -- this asserts parity with the Recommended Properties card's own press feedback rather than inventing specific values. Requested via Testmo review (B Mobile Apps, 2026-08-13).

---

### Verify the Recently Viewed carousel renders correctly when a standard phone is rotated between portrait and landscape.

**Section:** 12. Entry Points, Devices & Compatibility

**Description**
```gherkin
Given the test user is assigned to the `recently_viewed_variant` experiment group
And the Recently Viewed carousel is displayed with at least 3 listings
And the test device is a standard (non-foldable, non-tablet) phone
When the user rotates the device from portrait to landscape
And the user rotates the device back to portrait
Then the section and carousel re-render at each orientation's width with no cropped, stretched, or overlapping cards
And the carousel's leading card is unchanged across both rotations
And all card fields remain fully legible in both orientations
```

**Expected Result**

1. In landscape, the section and cards resize to the new width with no cropped, stretched, or overlapping content.
2. The carousel remains scrolled to the same leading card after rotating in either direction.
3. All card fields remain fully legible in both orientations, with no truncation beyond the designed ellipsis.

**Notes:** Distinct from cases 73/74, which cover iPad and Fold rotation specifically -- this covers standard (non-tablet, non-foldable) phone rotation, a gap in the existing device-matrix coverage. Requested via Testmo review (B Mobile Apps, 2026-08-13).

---

## Still open — not yet applied

- **Case 5** (`null` config resolution) — H Mobile Apps flagged the two-step `When` clause as "irrelevant," exact requested change still unconfirmed. Only the precondition count (3→1) has been touched; the structural objection has not.
- **1-vs-3 view-count contradiction** — one reviewer comment says the Home carousel needs only 1 viewed property to appear (applied across cases 1, 2, 3, 5, 6, 7, 9, 10, 49, 56, 57, 68, 72); a later comment on case 4 says "we do show the carousel after 3." Not resolved. If 3 turns out to be correct, all of those cases need to revert, and case 9 (the dedicated "exactly 1 view" boundary case) needs to become a below/at/above-3 triad instead.
