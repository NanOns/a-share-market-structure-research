---
stage_id: V4_R21_R4_CONTRACT_APPROVAL_SOURCE_REVISION_BINDING_R49_20261017
baseline_sha: 9f39ea57d51c35d7f288a104ff8df7bfbc5ef156
branch: codex/v4-workspace-cleanup
status: APPROVAL_BINDING_CODE_AND_OFFLINE_REGRESSION_COMPLETE_LIVE_PG_ACCEPTANCE_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
matrix_code_level_pg_paths_pending_live_reconciliation: 37
matrix_open_rows: 221
matrix_ingress_adapters_open: 8
next_stage: continue contract Head Authority descriptor daily and DM-01 consumer call chains; migrate remaining exact-mapped business reads
---

# V4 R21-R4 contract approval source-revision binding (R49)

Date: 2026-10-17 (Asia/Shanghai).

## Scope and changes

- Tightened the immutable contract-registry publication guard: an approval event is eligible only when its `source_revision` equals the exact `contract_versions.source_revision` selected by the publication binding.
- Tightened the PG reader to reject approval events with blank approver/reference values or a source revision different from the bound contract version.
- Added regression cases for blank approval identity and source-revision substitution. Existing active publication and market-calendar readers already call the registry loader inside their read-only repeatable-read transaction; this batch strengthens that call chain and does not add a parallel registry path.
- This is code and draft-SQL work only. The migration SQL remains unapplied pending its separately governed catalog and migration authorization.

## Original P1 accounting

- Original inventory denominator: **266** (200 Owner, 28 other business, 38 external market-source reads).
- Formally completed from the original 266: **0**. Formally remaining: **266**. This batch does not close any original inventory row because live accepted-publication / same-T0 PG readback and row-level reconciliation remain absent.
- Existing matrix evidence remains **37** PG-only code paths awaiting live reconciliation, **221** rows OPEN, and **8** ingress adapters OPEN. These are implementation-state counts, not formally completed business items; do not add them to infer formal closure.
- Unmapped reference edges remain 22.

## Verification and limits

- **33 passed** across `test_v4_contract_registry_pg_v1.py`, `test_v4_pg_publication_contract_static.py`, and `v4_publication_reader_di_r1/test_explicit_views.py`.
- The tests establish code and contract behavior only; they do not establish live database approval state, migration execution, or complete business acceptance.
- No PG DDL/DML, contract import, Head switch, source acquisition, service start, or production deployment was performed. No compliant reader/writer DSN is available in this environment.

## Next stage

Continue direct consumer migration across the contract, Head, Authority, descriptor, daily and BFF chains, then DM-01 PG-state orchestration and exact-mapped business reads. Keep the original formal count at 266 until approved live evidence supports per-row closure.
