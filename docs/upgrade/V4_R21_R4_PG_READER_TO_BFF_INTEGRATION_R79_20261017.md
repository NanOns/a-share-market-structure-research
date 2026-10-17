---
stage_id: V4_R21_R4_PG_READER_TO_BFF_INTEGRATION_R79_20261017
branch: codex/v4-workspace-cleanup
baseline_head: 411dcd12c
status: REAL_READER_TO_CURRENT_ADAPTER_CALL_CHAIN_VERIFIED_WITH_CONTROLLED_PG_BOUNDARY
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# PG publication reader to current BFF integration

The current-candidate BFF test now runs the actual `PgPublicationReader` and `PgV4CurrentAdapter` together against a controlled PostgreSQL-shaped connection. The fixture binds both the test contract and `V4_PG_WORKSPACE_OWNER_MAPPING_REGISTRY_R1` to one accepted publication. The reader resolves the exact contract bytes and approval evidence, derives the workspace mapping from those publication-bound bytes, reads the Owner families in the same context, and the summary endpoint returns the mapping and its contract digest. The test also checks that the contract query uses the exact publication-bound contract ID, version, and digest.

Verification: `tests/test_v4_pg_publication_candidate.py tests/test_v4_workspace_owner_mapping_pg.py` — **56 passed**. This verifies application call wiring and query parameters with a controlled adapter; it does not establish live PostgreSQL schema compatibility, authorized workspace mapping, production BFF rendering, or business acceptance. CI for the R78 implementation completed successfully: run `39030249085`.

Original 266 stable-ID accounting is unchanged: **0 formally complete; 266 remaining**. Code-level PG paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. This integration test closes no stable callsite ID.

Next: continue actual code migrations for the remaining current Head, Authority, descriptor, daily and BFF consumers. DM-01 main orchestration remains blocked at its file-backed accepted-Head/report authorities until their exact PG identity and source relation are established. No PG DDL or DML was run.
