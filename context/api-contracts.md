# API Contracts — Observed, Not Documented

**Read this first.** Every contract in this file must be derived from a real mitmproxy
capture of the shipped app. We have no source access and no API documentation, so this
file records *what we observed*, with the build it was observed on and the date. An entry
without a capture reference is not a contract — it is a rumour.

`tools/oracle.py` and `tools/har_diff.py` both read this file. `har_diff.py` compares new
captures against the recorded shapes and flags added / removed / retyped fields.

**Status:** template only. No captures taken yet. Every entry below is
`[ASSUMED — verify]` and exists to show the required shape.

---

## Capture procedure (do this before trusting anything below)

1. Start mitmproxy: `mitmdump -w runs/<run_id>/capture.flow --set hardump=...`
2. Point the device at the proxy; install the mitm CA cert.
3. **Certificate pinning check.** If the app pins certificates, the capture will fail and
   this entire oracle strategy is blocked. Test this on day one — see `docs/RISKS.md`.
   `UNKNOWN — needs manual verification`.
4. Exercise the flow; export HAR.
5. Record below: endpoint, method, key request params, response shape, and the fields the
   UI actually renders.

## Contract record format

Each endpoint gets:

- **Observed on** — app version + build, device, date, capture file path.
- **Request** — method, path, params that matter to us.
- **Response (fields we depend on)** — only the fields a test or the oracle reads.
  Do not transcribe the whole payload; record what we assert against.
- **UI mapping** — which screen and element each field lands in. This is the oracle link.
- **Fragility** — what breaks if this changes.

---

## `[ASSUMED — verify]` E1 — Search / listings

- **Observed on:** `TODO` — no capture yet
- **Request:** `GET|POST TODO` — search endpoint. Params expected to carry:
  purpose, location IDs, property type, price min/max, beds, baths, area min/max,
  furnishing, completion status, rent frequency, page, page size, sort.
- **Response (fields we depend on):**

  | Field | Type | Used for |
  |---|---|---|
  | `TODO total_count` | int | Result-count header assertion |
  | `TODO hits[]` | array | The result set the oracle diffs against the UI |
  | `TODO hits[].id` | string/int | **Primary oracle key** — must be visible or derivable in the UI |
  | `TODO hits[].price` | number | Price rendering + currency conversion checks |
  | `TODO hits[].rooms` / `baths` | int | Filter-correctness assertions |
  | `TODO hits[].area` | number | Area filter + unit conversion |
  | `TODO hits[].purpose` | enum | Filter correctness |
  | `TODO hits[].verified` / TruCheck flag | bool | Badge correctness |
  | `TODO page`, `page_size` | int | Pagination correctness |

- **UI mapping:** `search_results_list` → result-count header, listing cards.
- **Fragility:** if `hits[].id` is not exposed anywhere in the UI (not as text, not as an
  accessibility id, not in the share link), the oracle cannot match server rows to
  rendered rows and we fall back to weaker matching on price+title. **Establishing a
  stable listing ID visible to the UI is a top-3 ask in `docs/ASKS.md`.**

## `[ASSUMED — verify]` E2 — Listing detail

- **Request:** `GET TODO /listing/<id>`
- **Fields we depend on:** id, price, purpose, rooms, baths, area, amenities[],
  agent{id,name,phone}, agency{id,name}, verified flag, images[].
- **UI mapping:** `listing_detail`.
- **Fragility:** LDP is the assertion surface for most Tier-1 cases.

## `[ASSUMED — verify]` E3 — Lead submission (call / whatsapp / email)

- **Request:** `POST TODO` with listing id, agent id, lead type, contact details.
- **Why it matters:** this is the revenue event. A lead POST that silently 4xx's while
  the UI shows success is the highest-severity defect class in the app.
- **Assertion:** UI success state **must** be corroborated by a 2xx on this call.
  Test it explicitly: force a 500 via mitmproxy and confirm the UI does **not** claim
  success. `[ASSUMED — verify]` that the app even makes such a call before showing
  success — it may fire-and-forget.

## `[ASSUMED — verify]` E4 — Autocomplete / locations

- **Request:** `GET TODO /locations?q=`
- **Fields:** location id, name (en/ar), type/level, parent.
- **Fragility:** location IDs are the stable handle for deep-link test setup.

## `[ASSUMED — verify]` E5 — Auth

- **Request:** `POST TODO /login`, token refresh.
- **Note:** record token lifetime — it determines whether a session-scoped driver can
  outlive a long suite. Never record real credentials here; use `.env`.

## `[ASSUMED — verify]` E6 — Config / feature flags

- **Request:** `GET TODO /config`
- **Why it matters:** if remote flags gate features, a red test may mean "flag off", not
  "defect". `failure-triage` needs the flag snapshot in every evidence bundle, or it will
  misclassify. Capture this response on **every** run.

---

## Fault injection matrix (mitmproxy)

We do not wait for errors to happen. We cause them.

| Injection | Applied to | Expected app behaviour |
|---|---|---|
| HTTP 500 | E1 search | error state + retry; never a silent empty list |
| HTTP 401 | any authed call | re-auth prompt; user action preserved |
| Timeout / no response | E1, E2 | bounded spinner then error; never indefinite |
| Empty `hits[]`, `total_count: 0` | E1 | empty state, not a spinner or stale list |
| `total_count` ≠ `len(hits)` | E1 | header must not lie — pick a defined behaviour and hold to it |
| Truncated / malformed JSON | E1, E2 | graceful error, no crash |
| Very large `total_count` | E1 | no overflow or formatting break in EN or AR |
| Slow response (3G profile) | all | skeletons, no ANR |
| 500 on E3 lead POST | contact flow | **must not** show success |

## Change-detection workflow (`har_diff.py`)

1. Capture a HAR on every release build for the same scripted flow.
2. `python tools/har_diff.py --baseline runs/<prev>/capture.har --candidate runs/<new>/capture.har`
3. Any added / removed / retyped field is reported to `control-tower` as a
   **contract change**, not a defect — the dev team may have shipped it deliberately.
   Our job is to notice it before it surprises us in production.

## Known unknowns

- `UNKNOWN — needs manual verification`: certificate pinning. **Blocks everything above
  if present.** Test first.
- `UNKNOWN — needs manual verification`: whether the app uses GraphQL, REST, or both.
  Changes the diffing approach entirely.
- `UNKNOWN — needs manual verification`: response compression / binary protobuf payloads,
  which would make HAR-based diffing impractical.
- `UNKNOWN — needs manual verification`: whether any search filtering happens client-side.
  Client-side filters are invisible to the oracle.
