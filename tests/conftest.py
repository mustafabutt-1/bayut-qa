"""Pytest fixtures for the Bayut Android suite.

PLACEHOLDER — implemented in Phase 2. Deliberately left un-stubbed so that an
accidental early run fails loudly rather than silently collecting zero tests.

Phase 2 will provide:
  * session-scoped Appium driver (one per device shard)
  * function-scoped app-state reset (app data clear + relaunch)
  * per-test logcat and screenrecord capture
  * automatic artifact write to runs/<run_id>/<test_id>/
  * opt-in mitmproxy fixture (MITM_ENABLED) for the API oracle

See CLAUDE.md for the rules these fixtures must honour: explicit waits only,
no silent retries, and artifacts sufficient for bug-report-writer without any
additional input.
"""

raise NotImplementedError(
    "tests/conftest.py is a Phase 0 placeholder. Complete Phase 2 before running pytest."
)
