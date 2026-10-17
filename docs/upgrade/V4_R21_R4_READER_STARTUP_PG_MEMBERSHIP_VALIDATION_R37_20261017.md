---
stage_id: V4_R21_R4_READER_STARTUP_PG_MEMBERSHIP_VALIDATION_R37_20261017
branch: codex/v4-workspace-cleanup
status: PG_MEMBERSHIP_AND_IDENTITY_VALIDATION_WIRED; CURRENT_HEAD_NOT_MAPPED
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue accepted Head-to-BFF business invocation mapping and migrate remaining eligible reader callsites
---

# V4 R21-R4 Reader startup PG membership validation

Date: 2026-10-17 (Asia/Shanghai). Before this change, `validate()` still opened the membership snapshot and its membership/identity source files even when the candidate Head carried `native_membership_reference`. The latest applicable project execution contract and R36 descriptor wiring report were reviewed before implementation.

## Implemented

- Added a membership validation branch to the active `OperationalSuccessorReaderV1` admission function. With a Head-bound PG membership authority, it obtains the versioned context snapshot and reads the membership and identity references through their PG authority readers.
- It checks the exact candidate snapshot ID and rejects PIT-eligible metadata before accepting the PG branch. A candidate without the PG authority keeps the legacy, exact file-binding checks.
- Added a focused control that forbids local membership-file access and confirms both PG readers are invoked.

## Verification and limits

- Focused selection: **7 passed, 10 deselected** across the Reader integration, native membership reference and BFF descriptor tests.
- An unfiltered run of the same files produced **15 passed and 2 failed**. The two failing tests invoke `prepare()` and attempt a real PG append; they stop at the explicit `V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK` guard because no write DSN is configured. No fake DSN, database write or altered test semantics were used. These cases remain pending an authorized PG environment.
- R36 push CI run `39015066650` passed; run `39015064536` was still in progress at this report. No current accepted Head carries the PG membership authority, and no live PG readback, BFF request, service startup or P1 business acceptance occurred.

## Accounting

The original P1 baseline is **266**: 200 Owner, 28 other-business and 38 external-source reads. Formally complete **0 / 266**; formally remaining **266 / 266**. The existing inventory records 21 code-level PG paths pending live readback/reconciliation, 8 ingress adapters open, 237 other callsite rows open and 22 unmapped reference edges. R37 closes no original baseline item.

## Next stage

Continue the accepted Head-to-BFF invocation chain and migrate other callsites that can be mapped from existing contracts. Reconcile P1 counts only with exact callsite identity and permitted same-T0 Reader evidence. Keep PG write operations, Head activation and production changes outside this batch.
