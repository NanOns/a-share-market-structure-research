---
stage_id: V4_R21_R4_MEMBERSHIP_CONTEXT_CONTRACT_VERSION_R35_20261017
branch: codex/v4-workspace-cleanup
status: MEMBERSHIP_CONTEXT_METADATA_HAS_EXACT_VERSIONED_CONTRACT
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue operational Head/Authority/descriptor live-callchain preparation
---

# V4 R21-R4 membership context metadata contract version

Date: 2026-10-17 (Asia/Shanghai). This batch tightens R34's additive PG membership context contract before using it as runtime authority.

## Implemented

- Membership snapshot context metadata is now wrapped by the explicit `V4_NATIVE_MEMBERSHIP_CONTEXT_METADATA_R1` contract at version `1.0.0`.
- The Reader requires the exact contract ID/version, exact field set, exact Head T0/snapshot/snapshot ID bindings, and non-PIT flags. Older unversioned metadata fails closed; no filesystem fallback is added.
- The Authority's existing PG manifest contract remains unchanged; the metadata sub-contract is independently identified and versioned.

## Verification and limits

- Four focused tests passed for authority preparation, metadata contract validation, operational HTTP context routing, and Owner PG validation without opening Owner payload files.
- Python compilation and `git diff --check` passed.
- R34's GitHub Actions run was still in progress during this batch. No live PG read, service, publication readback or business acceptance occurred.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending full inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This contract-version correction closes no baseline row.

## Next stage

Continue wiring accepted Head, Authority, descriptor and BFF call chains. Keep all 266 formal items open until an approved Reader identity, mapped Head and same-T0 business readback are available.
