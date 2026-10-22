# Ninth Batch Follow-up R2: Exact Membership, Identity and RPS5 Endpoint

**Status:** `EXACT_DATED_MEMBERSHIP_AND_IDENTITY_RECOMPUTED_DEV_CANDIDATE_ONLY_NOT_PUBLISHED`
**Branch:** `codex/v4-unified-development`
**Development PG:** `127.0.0.1:5432/market_research`
**Web:** 28766 remains on the 10/21 token; 28765 untouched.

## Repairs

The RPS replay originally used same-day BaoStock membership after reading PG candidate authority, used the 10/15 RPS in its own price coordinate, and mapped securities only through the static accepted identity. The last issue omitted two currently active newly listed securities whose real source keys exist in the exact candidate's date-scoped PG identity authority.

`corrected_owner_replay.materialize_core` now validates exact candidate date and PG identity reference, uses the candidate-bound identity rows/source keys, applies exact date membership after same-day provider rosters, and computes prior endpoint RPS in the target date's affine QFQ coordinate. Candidate membership/identity authority references and identity-set digests are in the owner source closure.

The recompute used frozen TDX archive SHA `0404bbaeb985b2409a99dfcfe2c67b00e5dd574378105c408486183e9e058ede` and GBBQ SHA `c2f07f4aa8a9e8893e5dc24c1a83ac63f2ab27198ecde444154fd591c73e2739`. It used exact PG authorities for 10/13, 10/14, 10/15, 10/19 and 10/20. No provider login, sampled positive data or synthetic source values were used.

## Independent numeric check and UNKNOWNs

The independent verifier recalculated six-session returns from the saved TDX QFQ closes, independently ranked 10/15 and 10/20 with each exact PG identity set, and compared `RPS5(10/20) - RPS5(10/15)` and current RPS5 row by row. For all 5,226 core rows it found 5,202 observed exact matches, 24 matching UNKNOWNs and zero numeric mismatches. The endpoint UNKNOWN count fell from 2,399 to 24.

All 5,224 existing formal D0 rows now join to the corrected core; the independent frozen scanner returns TRUE/FALSE/UNKNOWN = 137/5,015/72 with zero scenario mismatches. Two exact current candidate members still have no formal D0/prewatch row, so the full 5,226-member D0 owner and downstream Focus/Priority outputs are not complete. They remain absent from the D0 artifact; no scenarios were invented.

## PG and route state

Independent PG readback still confirms the previously published 10/19–10/21 D0 closures as `DEV_ASOF_SOURCE_VERIFIED` with exact SourceIngress matches and PIT flags false. The new corrected 10/20 core/D0 subset has not been rebound into a successor R8 candidate or published to D0 PG, and 28766 has not read it under a new token. The 10/16 membership successor also still needs sequential R8 publication and route closure.

The earlier R1 report's two unmatched IDs were resolved by adding the exact PG candidate identity source keys. R2 supersedes its RPS row count (5,226 total, 24 UNKNOWN) and formal-D0 join coverage.

Evidence: [`NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R2_EVIDENCE.json`](NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R2_EVIDENCE.json), [`NINTH_BATCH_RPS5_ENDPOINT_INDEPENDENT_ROWS_R2.jsonl.gz`](NINTH_BATCH_RPS5_ENDPOINT_INDEPENDENT_ROWS_R2.jsonl.gz), and [`NINTH_BATCH_D0_FORMAL_RECOMPUTE_20261020_R3.jsonl.gz`](NINTH_BATCH_D0_FORMAL_RECOMPUTE_20261020_R3.jsonl.gz).
