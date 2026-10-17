---
stage_id: V4_R21_R4_PROFILE_CORRECTION_APPLY_PG_CONSUMER_R82_20261017
branch: codex/v4-workspace-cleanup
status: PROFILE_CORRECTION_APPLY_BOUNDARY_VERIFIED_LIVE_PG_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Profile correction `apply` consumer evidence

Extended R80's consumer boundary tests through the real semantic correction `apply` function. The test supplies a controlled Head-bound PG authority manifest and a PG-shaped correction row, then exercises source-owner conservation, descriptor validation, original-row digest validation, field-scope validation and replacement output. A separate case confirms missing Head authority fails closed before any local authority read.

Verification: **41 passed** across the R80/R82 Profile authority, Owner manifest, append-scope and contract-registry reader selections. These fixtures verify code paths only. Live database identity, accepted Head, namespace/publication and business dataset acceptance remain unverified.

The original stable-ID counts do not change in this test follow-up: **53** code-level PG paths pending live reconciliation; **203 OPEN**; **10 ingress-open**; **213 open or ingress**; **22 unmapped edges**; **0/266 formally complete** and **266/266 formally remaining**.
