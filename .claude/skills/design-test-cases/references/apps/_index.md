# App knowledge bases

Every suite is designed for exactly one app. Its knowledge base file supplies both the mechanical config (languages, devices, Testmo project, deeplink domains) **and** the domain knowledge (product model, key flows, regression-critical areas, known gotchas) that makes the resulting cases feel native to that app.

**Read the whole file for the target app, and read exactly one.** Do not load them all — that is what this index is for. The file is short enough to read in full, and Sections C–F are the reason it exists.

## Routing table

| Knowledge base file | App | Also called |
| --- | --- | --- |
| `bayut-uae.md` | Bayut UAE | Bayut, BUAE |
| `bayut-ksa.md` | Bayut KSA | Bayut SA, BKSA |
| `bayut-egypt.md` | Bayut Egypt | BEG |
| `bayut-gcc.md` | Bayut GCC (Oman etc.) | Bayut Oman |
| `dubizzle-egypt.md` | Dubizzle Egypt | |
| `dubizzle-gcc.md` | Dubizzle GCC (KSA, Bahrain etc.) | Dubizzle SA, Dubizzle Bahrain |
| `zameen-pk.md` | Zameen PK | Zameen |
| `olx-pk.md` | OLX PK | OLX Pakistan, OLX |
| `hatla2ee.md` | Hatla2ee | Hatla2ee Egypt |

`_template.md` is the blank to copy when adding an app.

## Choosing the file

1. If the person names the app, use it.
2. If the ticket, BRD, or Figma link identifies it (a domain, a Testmo project ID, a ClickUp space), use that and say which you inferred and why.
3. If it is still ambiguous — and note that several apps span the same markets (two apps in Egypt, two in Pakistan, GCC groupings that overlap) — **ask**. Do not default to Bayut UAE because its knowledge base is the most complete.

## When a feature ships to several apps

Common for shared platform work. Design the suite once against the **primary** app, then add a short delta section per additional app covering only what differs — usually language set, vocabulary, device matrix, and any regression-critical area unique to that app. Do not regenerate the whole suite per app.

Upload each app's suite to its own Testmo project.

## Completeness

Only `bayut-uae.md` is partially populated with real evidence, and even it awaits its regression checklist for Section E. The rest are stubs: config and vocabulary carry unconfirmed starting hints, and the domain sections are `TODO`.

**Never fill a TODO with a guess.** When a needed value is missing:

- Ask the person for it.
- Design the rest of the suite around the gap.
- Offer to record the answer into the knowledge base via the `update-knowledge` skill so the next person does not have to answer it again.

## Adding an app

Copy `_template.md`, fill what you know, leave the rest as TODO, and add a row to the routing table above. A partly-filled knowledge base is useful; one full of guesses is not.
