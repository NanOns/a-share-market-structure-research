---
stage_id: V4_R21_R4_BFF_PG_IDENTITY_CONSUMER_BATCH_R10_20261017
baseline_sha: daa5244ca83da42c4689b85361dce612957d3cc5
branch: codex/v4-workspace-cleanup
status: BFF_PG_IDENTITY_CALL_VERIFIED_LIVE_SOURCE_RECONCILIATION_OPEN
callsite_id: V4-BCA-R2-f50330e115a40dfbb290
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue daily source/identity Owner publication binding and exact other-business callsites
---

# V4 R21-R4 Core Product BFF identity consumer batch

Date: 2026-10-17 (Asia/Shanghai). This batch exercises the existing BFF-to-PG path as a business consumer.

## Verified call chain

- Matrix callsite `V4-BCA-R2-f50330e115a40dfbb290` identifies `CoreProductBFFR1.identity_records` at baseline line 673. The BFF calls `v4_membership_reference_pg_v1.read_search_identity` with the candidate's `native_membership_reference` authority binding and returns the PG rows together with the exact source binding.
- Added a consumer-level positive test that calls the BFF method, verifies the PG reader receives the selected candidate, and verifies the result is cached with its source binding. Added a missing-authority test proving the BFF returns `NATIVE_SEARCH_IDENTITY_REQUIRED_NO_FILE_FALLBACK`.
- The test exercises the present BFF-to-PG API call with a controlled PG reader substitute. It does not attest a live candidate, database role, database identity, exact production source SHA, or live PG row parity.

## Accounting

The matrix row's migration evidence is now populated, while its formal migration status remains `IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION`. Original P1 baseline is **266**, formally closed **0 / 266**, remaining **266**. Status totals remain OPEN 237, ingress-open 8, PG-code-pending-live-read/reconciliation 21; 22 reference edges remain unmapped.

## Verification

- **70 passed** across membership reference, BFF candidate routing, publication candidate, and contract registry tests. `git diff --check` passed. No live PG connection or writes ran.

## Next stage

Continue migrating daily source/identity Owner reads using the approved publication-bound identity relation and exact source semantics. Then progress the remaining other-business consumers by stable callsite ID.
