stage_id: R21-R4-candidate-index-producer-to-pg-owner-r61
branch: codex/v4-workspace-cleanup
status: EXACT_DAILY_CANDIDATE_INDEX_PRODUCER_AND_EXECUTOR_NOW_HAND_OFF_TO_PG_OWNER
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22

# R61 exact-daily candidate index to PG Owner chain

Date: 2026-10-17 (Asia/Shanghai). Reviewed R21-R4 task card, R60 source-freeze audit, R55 candidate-index PG authority and exact 266-row matrix.

## Implemented

- The new `producer_candidate_index_pg_v1.build_review_and_display_candidates` is selected for exact-daily candidates. It produces the optional current-T0 candidate components, builds a current-T0-only `PRODUCER_CANDIDATE_INDEX_V2` document in memory, and returns it to the caller. It does not read, merge, or write `data/v4/producer_candidate_index_v2.json`. The existing non-exact `producer_bootstrap_v1` flow remains unchanged.
- `operational_daily_executor_v1.derive_ready_sources` passes the producer document directly to `v4_membership_reference_pg_v1.prepare_research`. The file-read edge at the exact matrix row is removed. Missing or wrong-T0 producer output fails closed.
- Non-exact/historical candidate generation keeps its existing local index behavior. The exact PG BFF consumer still reads the index entry from Head-bound PG authority and has no file fallback for current exact T0.

## Verification and limits

- Focused tests: **28 passed** across the new producer/executor regression, PG reference, historical producer continuation, daily executor and pre-next-T0 chain.
- The new regression invokes the actual `build_review_and_display_candidates` function with an exact-daily candidate and proves a pre-existing local index remains byte-identical while the returned index contains only the current T0. A source assertion checks the executor no longer refers to the index filename.
- Full repository-policy selection: **278 passed**. Push CI `39023065604` and PR CI `39023067791` both completed successfully (Repository content policy). No live PG write/readback, source capture, service start, Head CAS or production operation was performed.

## Exact row accounting

The original denominator remains **266** (200 Owner, 28 other-business, 38 external market-source). Exact row `V4-BCA-R2-251b6859286f1bec50bc` moved from OPEN to PG code implemented pending live reconciliation. Matrix totals are **48 code-level PG paths**, **210 OPEN**, **8 active ingress adapters**, **218 open or ingress**, **22 unmapped edges**. Formal completion stays **0/266** and formal remaining **266/266**.

## Next

Continue all independent business consumers. Resolve current operational Head and DM-01 lifecycle/source-state ownership before changing any mutable Head or candidate-to-publication authority.
