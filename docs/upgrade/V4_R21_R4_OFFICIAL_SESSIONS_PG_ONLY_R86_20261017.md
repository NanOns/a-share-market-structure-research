---
stage_id: V4_R21_R4_OFFICIAL_SESSIONS_PG_ONLY_R86_20261017
branch: codex/v4-workspace-cleanup
status: OFFICIAL_SESSIONS_PG_ONLY_CODE_VERIFIED_LIVE_CALENDAR_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Shared official-session reader

`market_source_acquisition.official_sessions` now rejects FILE mode and the `V4_DATA_ACCEPTED_HEAD.json` plus calendar-file fallback is removed. Existing production callers share the configured PG market-calendar reader. Original stable ID `V4-BCA-R2-66c06ef7f4ecead04533` now records the exact reader behavior and tests; it remains pending live calendar registration, accepted publication identity and T0 reconciliation.

Verification: **34 passed** across shared official-session behavior, PG market-calendar reads, candidate BFF calendar consumer, and daily executor chains. PG snapshots were controlled fixtures; no live calendar acceptance is claimed.

Original accounting remains **0/266 formally complete; 266/266 remaining**. Code-level PG paths pending live reconciliation: **53**; OPEN: **203**; ingress-open: **10**; open or ingress: **213**; unmapped reference edges: **22**. No live PG read/write occurred.

Next: remove explicit FILE authority for BaoStock runtime acceptance and continue the remaining current Head, Owner and BFF migrations with stable-ID evidence.
