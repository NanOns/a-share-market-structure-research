# Ninth Batch Follow-up: Exact RPS5 Endpoint Repair

**Status:** `REAL_FROZEN_SOURCE_RECOMPUTED_DEV_CANDIDATE_ONLY_NOT_PUBLISHED`
**Branch:** `codex/v4-unified-development`
**PG:** `127.0.0.1:5432/market_research` (date-scoped identity facts read only)
**Web:** 28766 remains on the prior 10/21 candidate; 28765 untouched.

## Findings and fix

The 10/20 RPS5 delta had been computed by subtracting the 10/15 RPS5 produced in its own price coordinate and by allowing a same-day BaoStock roster to override exact PG candidate membership. That caused 2,399 `EXACT_DATED_RPS_ENDPOINT_UNKNOWN` rows and 12 observed-delta mismatches in the first independent comparison.

`corrected_owner_replay.materialize_core` now accepts exact date-scoped candidate authorities, reads their PG-backed identity through `read_identity`, and applies those sets after provider roster ingestion. It recomputes the delta endpoint at the target date's TDX native affine QFQ coordinate, using the exact endpoint-date candidate universe. Membership authority, candidate token, identity set digest and source bindings are included in the source digest.

The replay used frozen TDX package SHA `0404bbaeb985b2409a99dfcfe2c67b00e5dd574378105c408486183e9e058ede` and GBBQ SHA `c2f07f4aa8a9e8893e5dc24c1a83ac63f2ab27198ecde444154fd591c73e2739`. PG candidate identity authorities for 10/13, 10/14, 10/15, 10/19 and 10/20 were read back with exact T0 and bound `native_membership_reference`; no BaoStock login or synthetic positive data was used.

## Numeric result

An independent calculation from saved TDX QFQ closes used six explicit official sessions at each endpoint, independently ranked valid 10/15 and 10/20 returns by their exact date-scoped PG candidate identity sets, and compared `RPS5(10/20) - RPS5(10/15)` row by row. It verified 5202 exact values, 22 matching UNKNOWNs and zero mismatches across 5224 rows. The 10/20 delta UNKNOWN count fell from 2,399 to 22.

The formal D0 owner was recomputed with the frozen scanner after applying the verified delta values: TRUE 137, FALSE 5015, UNKNOWN 72 (previous formal UNKNOWN: 2,373). The frozen scanner independently matched the recomputed output. Two security IDs in the prior D0 owner have no matching row in the recomputed core source; their prior UNKNOWNs remain unchanged.

## Candidate publication

The corrected core and D0 prewatch are source-bound recomputations only. They have not been rebound into a superseding R8 candidate, appended to D0 PG, or read through 28766. The published R8 token and dev Head remain unchanged; this report does not claim route or publication closure. The 10/16 exact-T0 Membership candidate still needs its sequential R8 publication/read-index closure.

Historical NON_PIT flags and prior D0 three-state rows remain intact.

Evidence: [`NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R1_EVIDENCE.json`](NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R1_EVIDENCE.json), [`NINTH_BATCH_RPS5_ENDPOINT_INDEPENDENT_ROWS_R1.jsonl.gz`](NINTH_BATCH_RPS5_ENDPOINT_INDEPENDENT_ROWS_R1.jsonl.gz), [`NINTH_BATCH_D0_FORMAL_RECOMPUTE_20261020_R2.jsonl.gz`](NINTH_BATCH_D0_FORMAL_RECOMPUTE_20261020_R2.jsonl.gz).


## Dev as-of Seal readback

Independent PostgreSQL readback confirms the prior exact-candidate D0 revisions for 10/19, 10/20 and 10/21 are `DEV_ASOF_SOURCE_VERIFIED`; all retain `AS_RECORDED=false`, `PIT_ELIGIBLE=false` and `production_admission=false`. Each consumed exactly one bound SourceIngress receipt, with expected package date `2026-10-21`, matching artifact digest/bytes and available time before the R8 snapshot cutoff. Their publication IDs, cutoffs, time chain and exact PG readback are recorded in the evidence JSON. The 10/16 superseding membership candidate still has not been R8/D0 published.
