stage_id: V4_R21_R4_CANDIDATE_BFF_REGISTRY_POSITIVE_NEGATIVE_R59_20261017
branch: codex/v4-workspace-cleanup
status: BFF_USES_APPROVAL_AWARE_REGISTRY_READER
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 47
open_callsite_rows: 211
ingress_adapters_open: 8
remaining_open_or_ingress: 219
unmapped_reference_edges: 22

# V4 R21-R4 BFF Registry positive and negative path batch

Date: 2026-10-17 (Asia/Shanghai). Reviewed the R4 Drive card, R58 report, current R21 callsite matrix and the R58 CI result before extending the BFF consumer path.

## Implemented

- The candidate BFF's official close-time contract consumer invokes the production `load_current_approved_contract` Registry reader in its runtime PG mode. R59 tests exercise that actual call path through a PG-shaped read-only repeatable-read snapshot, database identity attestation and contract approval rows.
- The BFF converts the Registry's approval/digest rejection into its controlled `ValueError` fail-closed path. A revoked version remains rejected even when a matching local contract file is present; there is no fallback.
- Explicit FILE mode remains available for bounded offline fixtures. It is not consulted when PG mode lacks a namespace or the PG Registry rejects the contract.
- The original 266-row matrix is unchanged: this is an active contract/BFF call path outside the exact row that still reads `producer_candidate_index_v2.json`. That index row remains OPEN until its producer and consumer are migrated together.

## Verification and limits

- Focused local selection: **35 passed** across the BFF Registry consumer, Registry approval/revocation reader and accepted-market-calendar tests.
- Repository-policy pytest selection: **298 passed** locally. R58 push and PR CI passed on `a7010fe34` (runs `39021898688`, `39021895275`); R59 CI is pending on the next pushed commit.
- PG behavior used a controlled fake snapshot. No live catalog read, contract import, registry write, server start or Head update occurred. This is a real application-consumer code path with synthetic PG evidence, not live business acceptance.

## Accounting

R59 changes no row status. The original denominator remains **266**: 200 Owner, 28 other-business and 38 external-market-source reads. Current reconciled matrix remains **47** code-level PG paths pending inventory reconciliation, **211 OPEN**, **8 ACTIVE_INGRESS_ADAPTER_OPEN**, and **22 unmapped reference edges**. Formally complete **0/266**; formally remaining **266/266**.

## Next

Continue replacing exact operational Head and candidate-index reads with the real PG owner/current-head relation. Keep solving DM-01 source/lifecycle report ownership and finish the TDX/BaoStock entrypoint audit. Do not count current Head equality checks or mocks as migration acceptance.
