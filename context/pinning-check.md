# Certificate Pinning Check

- **Verdict:** MITM_NOT_CONFIGURED
- **Checked:** 2026-08-10 13:23:53Z
- **Flow file:** (none configured)

No --mitm-flow-file given. The crawl will produce no API evidence and cert pinning stays UNRESOLVED.

## Why this matters

If the app pins certificates, mitmproxy sees nothing, and the API oracle (`oracle.py`) and contract diffing (`har_diff.py`) cannot be built. That is the most differentiated part of this QA design, so a PINNING_SUSPECTED verdict is a programme-level blocker, not a tooling inconvenience. The ask to dev is a debug build with a network security config that trusts user CAs.
