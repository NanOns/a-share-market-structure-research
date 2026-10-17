---
stage_id: V4_R21_R4_PG_BFF_WORKSPACE_MAPPING_CONTRACT_R78_20261017
branch: codex/v4-workspace-cleanup
baseline_head: dcd33658488fc111911760828bde317356a28a43
status: PG_CANDIDATE_BFF_WORKSPACE_MAPPING_BOUND_TO_PUBLICATION_CONTRACT
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# PG candidate BFF workspace mapping contract

Read the current R77 source-path stage and the formal R21-R4 execution card before this batch. The seven-endpoint PG candidate BFF now validates its root-to-namespace and Owner-schema mapping from the same publication-pinned PG contract set used for Head, module bindings, and Owner readbacks. The handler no longer loads the workspace mapping registry file. `PgPublicationReader` resolves the sanitized mapping from the exact approved `V4_PG_WORKSPACE_OWNER_MAPPING_REGISTRY_R1` contract in the accepted publication and current workspace identity; absent publication binding, root mapping, namespace, database identity, or Owner schema match fails closed.

Verification: **8 focused tests passed** across the seven-endpoint HTTP candidate route and mapping-contract positive/negative cases. The controlled HTTP adapter and synthetic mapping document verify code wiring and rejection behavior; they are not live PG business acceptance. The current repository registry has no authorized historical root mapping, so live candidate responses remain blocked until the mapping contract is approved and bound to an accepted PG publication.

Original 266 stable-ID accounting is unchanged: **0 formally complete; 266 remaining**. Code-level PG paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. This BFF wiring closes no P1 ID without exact stable-ID mapping and live same-T0 Owner readback.

Next: continue replacing file-backed current Head/Authority consumers with exact PG relations, and continue the 28 other-business / 200 Owner caller inventory. The DM-01 continuous-maintenance changes remain uncommittable until their report and local Head authorities are replaced; no admission rule is bypassed.
