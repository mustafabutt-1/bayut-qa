# House style for mobile test cases

This style is shared across every app in the group — Bayut, Dubizzle, Zameen, OLX, Hatla2ee. It does not vary by brand or market. What varies per app is vocabulary, languages and devices, and those come from the app knowledge base, not from here.

Derived from the DPV In-App Survey suite in Testmo (Bayut UAE, project 38, cases 2350611 and 2363626–2363666), which is the reference implementation. The worked examples below use that suite because it is the one with real evidence behind it; the rules apply unchanged to a Zameen or OLX Pakistan feature.

## Contents

- [The three fields](#the-three-fields)
- [Field 1 — Name / Summary](#field-1--name--summary)
- [Field 2 — Description (BDD / Gherkin)](#field-2--description-bdd--gherkin)
- [Field 3 — Expected Result](#field-3--expected-result)
- [Formatting conventions](#formatting-conventions)
- [Granularity](#granularity)
- [Anti-patterns](#anti-patterns)
- [Worked examples](#worked-examples)

## The three fields

Every case has exactly three parts. They map to Testmo fields on upload, so all three are mandatory — a case with an empty Description or Expected Result is not finished.

| Field | Answers | Written as |
| --- | --- | --- |
| Name / Summary | *What is being verified?* | One `Verify ...` sentence |
| Description | *How do I set it up and run it?* | A Gherkin scenario: Given / When / Then / And |
| Expected Result | *What must be true afterwards?* | Numbered observable assertions |

The three are different **zoom levels** on the same behaviour, not three chances to say the same thing. The Name is the scannable index entry. The Description is the recipe. The Expected Result is the pass/fail contract.

A tester who reads only the Name should know what the case is about. A tester who reads all three should be able to execute it without opening the BRD.

## Field 1 — Name / Summary

One sentence. Starts with `Verify`. Ends with a full stop. States the condition and the outcome together.

```
Verify the survey is not displayed when the `is_dpv_survey_enabled` remote config is disabled.
```

This is the field that appears in run lists and reports, so it has to read standalone. Never write `Verify all the above cases` or `Same as above` — ordering is not preserved in Testmo and a case that leans on its neighbours is broken.

Keep it to one line. If the setup is long, it belongs in Description, not in a growing title.

## Field 2 — Description (BDD / Gherkin)

The Description is a **Gherkin scenario**: Given / When / Then, with **And** for additional conditions, actions, or validations. This is the format the team reviews in, and it maps directly onto Testmo's BDD template on upload — one Gherkin clause becomes one Testmo step.

```
Given `is_dpv_survey_enabled` is set to False in Remote Config
And the test user has not been shown the survey in the last 48 hours
And the user is logged in on a Sale DPV
When the user generates a qualifying lead by tapping **Call**
And the user completes the lead flow and returns to the DPV
Then the survey bottom sheet is not displayed
And no survey analytics event is fired
And the rating & reviews nudge behaviour is unchanged
```

Rules:

- **Given = precondition.** The starting state: config values, auth state, cooldown state, language, device. State every precondition that is not the default — unstated preconditions are the main cause of results that cannot be reproduced.
- **When = action or system event.** What the user or system does. One action per clause.
- **Then = verifiable outcome.** What must be true afterwards. Observable only.
- **And** continues whichever clause type precedes it. Never start a scenario with And.
- **One logical behaviour per scenario.** Do not combine unrelated scenarios. If a scenario needs a second When block after a Then, it is two cases.
- **Keep clauses executable.** A manual tester should be able to perform each clause without opening the BRD.
- **Be concrete about test data.** "enters exactly 3 characters" beats "enters short text"; "taps **Call**" beats "generates a lead" when the lead type matters.
- **Write clauses without terminal full stops.** Gherkin convention, and it keeps the Testmo step text clean.
- **Do not restate the Name.** The three fields are different zoom levels, not three phrasings of one sentence.
- **Reference, don't reproduce.** For localisation or tracking assertions, point at the sheet and rows rather than pasting the table.

Three to ten clauses is the normal range. More than that usually means the case should be split.

## Formatting conventions

These apply across all three fields.

| Element | Convention | Example |
| --- | --- | --- |
| Config keys, event names, technical identifiers | Backticks | `` `is_dpv_survey_enabled` `` |
| UI labels the user sees and taps | Bold | `**Other**`, `**Submit**` |
| Exact copy strings under test | Double quotes | `"Which information do you find most useful when viewing a property?"` |
| Enumerations inside a sentence | Parenthetical with `e.g.` | `(e.g., Call, WhatsApp, Email, SMS)` |
| Screen and surface names | Plain text, as the team says them | DPV, LPV, Gallery View, bottom sheet |

Use the team's vocabulary. DPV, not "property details page", once the abbreviation is established.

## Granularity

One case, one verifiable behaviour. Split when the assertions are independent:

```
Verify users can select a single survey option.
Verify users can select multiple survey options.
```

Not `Verify users can select single or multiple survey options.` — those fail for different reasons, and one pass/fail hides which.

Keep together when one assertion is the direct consequence of the other:

```
Verify the "Other" text field does not accept more than 100 characters, and the 100-character
value is submitted and sent correctly in the analytics event.
```

The boundary and its downstream effect are one behaviour, and they become two numbered lines in the Expected Result rather than two cases.

A useful check: if a case's Steps contain a branch ("if X, do this, otherwise do that"), split it.

## Anti-patterns

**Empty or placeholder Expected Result.** `The feature works correctly.` The case can never fail. Every Expected Result must name something concrete.

**Prose steps instead of Gherkin.** `1. Open the app. 2. Tap Call.` The Description must be Given/When/Then — the uploader parses those keywords to build Testmo steps, and un-keyworded prose will not map.

**A second When after a Then.** That is two behaviours in one case. Split it.

**Assertions buried in Given or When.** `When the user taps **Submit** and the sheet dismisses` — the dismissal is a Then.

**Description restating the Name.** Wastes a field and drifts out of sync when one is edited.

**Missing Given clauses.** Especially remote config values and cooldown state.

**"Verify all the above cases..."** Expand it. Ordering is not preserved in Testmo.

**Compound cases with five bulleted assertions in the title.** Common in the older spreadsheets. Split into one case per assertion.

**Vague scope statements.** `Verify the feature on iPad as well.` Name the surface and the property, and put the device list in Given.

**Deferring entirely to a document.** `Verify events fire as per the tracking sheet.` is acceptable only as a catch-all alongside specific cases.

**Near-duplicates.** Two cases differing only in wording either waste an execution cycle or one gets skipped, silently dropping real coverage below reported coverage.

## Worked examples

### Remote config gating

**Name**
```
Verify the survey is not displayed when the `is_dpv_survey_enabled` remote config is disabled.
```

**Description**
```gherkin
Given `is_dpv_survey_enabled` is set to False in Remote Config
And the test user has not been shown the survey in the last 48 hours
And the user is logged in and viewing a Sale DPV
When the app is relaunched so the updated remote config value is fetched
And the user generates a qualifying lead by tapping **Call**
And the user completes the lead flow and returns to the DPV
And the user navigates to the LPV and opens a different DPV
Then the survey bottom sheet is not displayed on either DPV
And no pending-survey record is created
And no survey analytics event is fired
And the rating & reviews nudge behaviour is unchanged
```

**Expected Result**
```
1. The survey bottom sheet is not displayed after the lead is generated.
2. The survey bottom sheet is not displayed on the second DPV, confirming no pending-survey
   record was created.
3. No survey analytics event appears in GA DebugView at any point.
4. The rating & reviews nudge continues to behave as before.
```

Note assertion 4 — the BRD stated the rating & reviews nudge must be unchanged, so it belongs in the contract.

### Boundary validation

**Name**
```
Verify the "Other" text field accepts text from 3 up to 100 characters and the survey can be
submitted successfully.
```

**Description**
```gherkin
Given `is_dpv_survey_enabled` is True
And the survey bottom sheet is displayed on the DPV
And GA DebugView is attached to the device
When the user selects the **Other** option
And the user enters exactly 3 characters in the free-text field
And the user clears the field and enters exactly 100 characters
And the user taps **Submit**
Then **Submit** is enabled at 3 characters with no validation message
And the field accepts all 100 characters without truncation
And the survey submits successfully and the bottom sheet dismisses
And the analytics event carries the full 100-character value untruncated
```

**Expected Result**
```
1. At 3 characters, **Submit** is enabled and no validation message is shown.
2. At 100 characters, the field accepts all 100 characters without truncation and **Submit**
   remains enabled.
3. The survey submits successfully and the bottom sheet dismisses.
4. The analytics event carries the full 100-character value, untruncated.
```

### Cross-context state

**Name**
```
Verify the survey is displayed on the Rent DPV after generating a qualifying lead on the Sale
DPV, closing the app, and reopening the Rent DPV, while the analytics event sends the original
purpose as Sale and vice versa.
```

**Description**
```gherkin
Given `is_dpv_survey_enabled` is True
And no survey has been shown in the last 48 hours
And GA DebugView is attached to the device
When the user opens a Sale DPV and generates a qualifying lead
And the user kills the app from the app switcher before the survey is displayed
And the user relaunches the app and navigates to a Rent DPV
And the user selects any option and taps **Submit**
And the flow is repeated with the purposes reversed
Then the survey bottom sheet is displayed on the Rent DPV
And the analytics event sends `purpose = Sale`, matching the originating DPV
And the reversed run sends `purpose = Rent`
And the pending-survey record is cleared so the survey does not show again
```

**Expected Result**
```
1. The survey bottom sheet is displayed on the Rent DPV after relaunch.
2. The survey analytics event sends `purpose = Sale`, matching the DPV where the lead
   originated, not the DPV where the survey was displayed.
3. In the reversed run, the event sends `purpose = Rent`.
4. Returning to another DPV does not show the survey again.
```

The reversed run folds "and vice versa" into the scenario rather than spawning a near-duplicate case.

### Cross-cutting — device matrix

**Name**
```
Verify the survey UI/layout is displayed correctly on iPad and mini-screen iOS devices.
```

**Description**
```gherkin
Given `is_dpv_survey_enabled` is True
And the test devices are an iPad on the latest supported iPadOS and an iPhone 12 mini
And the approved Figma frame is open for comparison
When the survey is triggered via a qualifying lead on a DPV on each device
And the bottom sheet is compared against the Figma frame at both device sizes
And the user selects the **Other** option to open the keyboard
And the flow is repeated on iPad in Split View and Slide Over
And each device is rotated to landscape and back
Then the bottom sheet renders at the correct width and anchoring per the design on iPad
And all options and **Submit** remain reachable on mini screens
And the free-text field and **Submit** are not obscured by the keyboard
And the layout holds in Split View, Slide Over, and both orientations
```

**Expected Result**
```
1. The bottom sheet renders at the correct width and is centred/anchored per the design on
   iPad, with no stretched or full-bleed content.
2. On mini screens all options and the **Submit** button remain reachable; content scrolls
   rather than clipping.
3. With the keyboard open, the free-text field and **Submit** button are not obscured.
4. Layout holds in Split View, Slide Over, and both orientations with no overlap or
   truncation.
```

Compare to the generic `Verify the feature on iPad as well.` — same scenario, but this one tells the tester what to look at.
