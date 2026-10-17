---
stage_id: V4_R21_R4_OWNER_RUNTIME_NO_LOCAL_PAYLOAD_R26_20261017
branch: codex/v4-workspace-cleanup
status: OWNER_RUNTIME_VALIDATION_USES_PG_AUTHORITY_CURRENT_HEAD_OPEN
callsite_id: V4-BCA-R2-ce030238606ae3e34b44
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: migrate the accepted operational Head binding and exact daily Owner/source consumers
---

# V4 R21-R4 Owner runtime validation path

Date: 2026-10-17 (Asia/Shanghai). This batch removes a local Owner-payload read that happened before the R22 PG Owner reader ran.

## Implemented

- `OperationalSuccessorReaderV1` now loads its Head-embedded PG authority manifest before validating the candidate. It passes that authority into `validate()` and checks Owner dates/domains/source-binding digests against the manifest.
- Runtime validation no longer opens Owner payload files on this path. The PG manifest and every Owner descriptor are validated by the existing read-only PG authority reader; full payload reads remain in the domain `read()` call.
- The candidate-preparation path without a PG authority keeps its exact file-binding check. This preserves the explicit source-ingress/legacy preparation boundary and does not add runtime fallback.
- Matrix row `V4-BCA-R2-ce030238606ae3e34b44` records the added code-path evidence. It remains `OPEN`: the current accepted operational Head has no `native_pg_owner_authority`, so this runtime route is not wired to current authority.

## Verification and limits

- **11 passed** across embedded Owner Reader, Head-embedded product catalog, and BFF descriptor binding tests. New tests prove the PG-authority validation branch makes no Owner file open and the non-PG preparation branch still checks its file binding.
- A broader selection that included `tests/test_v4_embedded_owner_authority_v2.py` attempted nine PG append setup paths and failed because `V4_NATIVE_PG_DSN` is not configured. Those attempts performed no PG connection/write; they do not verify live authority append behavior.
- Compile and diff checks passed. No PG DDL/DML, contract import, accepted Head write, source acquisition, service, worker, or production operation ran.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending live readback/reconciliation; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This batch adds reader-path evidence but closes no callsite.

## Next stage

Migrate and bind `native_pg_owner_authority` into the accepted operational Head, then continue the exact daily source, Head, Owner and BFF chain. Keep all formal counts unchanged until accepted Head and same-T0 Owner/source readback and row reconciliation pass.
