# Testmo mapping

Reference for how a designed suite lands in Testmo. The upload itself is the `upload-to-testmo` skill — this file is the shared reference both skills read.

## API facts

These are verified against the live instance. Do not substitute assumptions.

| | |
| --- | --- |
| Create | `POST /api/v1/projects/{project_id}/cases` with body `{"cases":[ {...} ]}` |
| Required field | `name` only |
| BDD template | `template_id: 2` |
| Steps | `custom_steps[]`, each `{ "text1": <clause HTML>, "text3": <expected result HTML> }` |
| Auth | `Authorization: Bearer $TESTMO_API_TOKEN` |
| Instance | `https://dubizzlelabs.testmo.net` (`TESTMO_SITE=dubizzlelabs`) |

### Hard limits

- **No update, no delete.** `PATCH`, `PUT`, and `DELETE` on cases all return 404. Every create is **permanent and additive**. A sheet edited after upload cannot be re-synced — corrections to uploaded cases are a manual edit in the Testmo UI.
- **Never DELETE a collection endpoint** to clean up. It risks wiping the project.
- **Duplicate protection is by case name** within the target folder. The uploader skips any case whose name already exists there; it cannot remove anything already created.
- **Tags must be simple tokens.** Spaces, slashes, and parentheses cause a **422 that rejects the entire batch**. The uploader sanitises them; a 422 in the wild is almost always a tag.

## Projects per app

Each app uploads to its own Testmo project. Take the ID from the app knowledge base; this table is the summary.

Site: **dubizzlelabs.testmo.net**

| App | Project ID | Features repo group | Repo URL |
| --- | --- | --- | --- |
| Bayut UAE | **38** | **79014** | `/repositories/38?group_id=79014` |
| Dubizzle Egypt | **40** | **79017** | `/repositories/40?group_id=79017` |
| Bayut KSA | TODO | TODO | |
| Bayut Egypt | TODO | TODO | |
| Bayut GCC | TODO | TODO | |
| Dubizzle GCC | TODO | TODO | |
| Zameen PK | TODO | TODO | |
| OLX PK | TODO | TODO | |
| Hatla2ee | TODO | TODO | |

Never upload one app's suite into another app's project. Confirm the project ID with the person before writing.

**Note on the number 299:** an earlier version of this file listed Bayut UAE as project 299. That was inferred from an export filename (`testmo-export-repository-299.csv`) and is a repository reference, not a project ID. The correct project ID is **38**.

## Field mapping

| Sheet column | Testmo | Notes |
| --- | --- | --- |
| Test Case | `name` | The scenario title |
| Description (BDD) | `custom_steps[].text1` | Parsed per Gherkin clause |
| Expected Result | `custom_steps[].text3` | Paired to `Then` clauses in order |
| Notes | — | Review aid; not uploaded |
| Testmo Case ID | — | Filled *after* upload, as a record. **Not** a sync link |

### Configurations column — confirmed present, at least on some projects

A live CSV re-export from a Bayut UAE Testmo project (2026-08) included a fifth column,
`Configurations`, holding a platform tag (`iOS` or `Android`) on device-specific cases —
alongside Case ID / Case / Description / Expected. This is not yet documented in the
upload JSON schema below and its write path via the API hasn't been verified the way the
facts above have. Where it's confirmed present on the target project, prefer it for
platform-scoping a case over only stating the platform in prose — it's structured data a
run view can filter on. Confirm on the target project before relying on it; do not
assume every project exposes it.

### How clauses map

| Clause | `text3` |
| --- | --- |
| Given / And-after-Given | "The precondition is satisfied." |
| When / And-after-When | "The action completes successfully." |
| Then / And-after-Then | the matching numbered assertion from Expected Result |

`And` and `But` inherit the preceding keyword. Assertions pair with `Then` clauses positionally, so **Expected Result order must match Then order**. Surplus assertions append to the final `Then` rather than being dropped.

### Tags

Every case is tagged with the **ticket ID**, `bdd`, and `claude-generated`.

## Input JSON schema

Phase 8 writes the spreadsheet; the uploader reads either the `.xlsx` directly or this JSON.

```json
{
  "feature": "DPV In-App Survey",
  "cases": [
    {
      "section": "Trigger & gating",
      "title": "Verify the survey is not displayed when the `is_dpv_survey_enabled` remote config is disabled.",
      "description": "Given `is_dpv_survey_enabled` is set to False in Remote Config\nAnd no survey has been shown in the last 48 hours\nWhen the user generates a qualifying lead by tapping **Call**\nThen the survey bottom sheet is not displayed\nAnd no survey analytics event is fired",
      "expected": "1. The survey bottom sheet is not displayed.\n2. No survey analytics event appears in GA DebugView.",
      "notes": ""
    }
  ]
}
```

`section`, `title`, `description`, and `expected` are all required. `notes` may be empty.

## Folders

**Each feature gets its own new folder** inside the app's Features repo group, and all of that feature's final cases go in it.

The reliable procedure:

1. Open the app's Features repo (URLs above).
2. Create a folder named for the feature, inside the group listed in the table.
3. Open the new folder and read its ID from the URL.
4. Pass that ID as `--folder`, or set `TESTMO_FOLDER_ID`.

Creating the folder by hand takes about ten seconds and removes all ambiguity about where cases land — worth it, given uploads cannot be undone.

The uploader has an experimental `--create-folder` flag that attempts creation via the API. **The folder-creation endpoint has not been verified on this instance**, unlike the case-creation facts above which have. If it fails, fall back to the manual steps. Do not let it silently pick a destination.

Before uploading, **check whether the target folder already contains cases**. Because there is no delete API, a folder holding a half-uploaded suite needs a human decision, not a guess.

## Token hygiene

Never print the token. Never commit it. Keep the env file at `chmod 600`. If it is exposed, say so plainly and advise rotating it immediately.
