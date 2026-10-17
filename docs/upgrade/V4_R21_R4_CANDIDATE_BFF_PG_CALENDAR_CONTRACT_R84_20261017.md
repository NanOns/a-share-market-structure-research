---
stage_id: V4_R21_R4_CANDIDATE_BFF_PG_CALENDAR_CONTRACT_R84_20261017
branch: codex/v4-workspace-cleanup
status: CANDIDATE_BFF_CALENDAR_CONTRACT_PG_ONLY_CONSUMER_VERIFIED_HEAD_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Candidate BFF calendar contract

`candidate_research_read_v2.capture_calendar_contract` now has no explicit file path. It loads `V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1` from the approved contract registry, binds the raw contract digest and namespace/database identity, and rejects `V4_DAILY_CONTRACT_SOURCE=FILE`. The active `read_candidates` path carries this PG binding into `first_capture_readiness`; the consumer test exercises that call chain and its fail-closed index boundary.

Verification: **6 passed** in `test_v4_r21_candidate_calendar_contract_pg.py`, including the real registry reader against a PG-shaped read-only snapshot, REVOKED approval rejection, missing namespace, FILE-mode rejection, and BFF callsite propagation.

No original stable ID is closed by this change: the original rows in `candidate_research_read_v2.py` still include local Head/candidate/predecessor reads whose canonical PG Head relation and legacy history mapping are unresolved. Counts remain **0/266 formally complete; 266/266 remaining**; **53** code-level PG paths pending live reconciliation; **203 OPEN**; **10 ingress-open**; **213 open or ingress**; **22 unmapped reference edges**. No live PG identity, accepted Head, namespace/publication/T0, or business acceptance was verified.

Next: remove and replace the remaining current Head and candidate-index file reads in this BFF using the exact canonical publication/Owner relations, then reconcile the original callsite IDs. Continue the remaining explicit FILE contract consumers and all other-business/Owner batches.
