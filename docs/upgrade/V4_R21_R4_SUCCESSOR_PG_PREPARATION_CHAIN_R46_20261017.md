---
stage_id: V4_R21_R4_SUCCESSOR_PG_PREPARATION_CHAIN_R46_20261017
branch: codex/v4-workspace-cleanup
status: EXACT_POLICY_SUCCESSOR_PREPARATION_NOW_WIRES_PG_HEAD_AUTHORITIES
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 33
ingress_adapters_open: 8
other_callsite_rows_open: 225
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_WRITE_DSN
next_stage: connect remaining operational callers and migrate period history/verifier through an approved artifact representation
---

# V4 R21-R4 successor PG authority preparation chain

Date: 2026-10-17 (Asia/Shanghai). The R45 predecessor reader, R44 daily evidence contract, R39 registry reader, membership reference contracts and current exact daily producer were reviewed before wiring the preparation path.

## Implemented

- Added `V4_SUCCESSOR_PG_AUTHORITY_PREPARATION_R1.prepare_remaining()`. The real publisher calls it under the publication lock for exact daily candidates, before validation and pointer CAS. It prepares or verifies the predecessor Head, builder registry and daily evidence PG facts; Owner and membership authorities remain prepared by the existing exact-policy builder.
- Updated the publisher's TDX guard to resolve the configured read-only source root, and removed embedded drive-letter paths. The G-drive engineering shadow check now validates the drive and temporary-root component without a machine-specific path literal.
- This closes the producer-to-Head wiring gap for the existing reader migrations. It introduces no new baseline callsite closure and does not imply that PG preparation or publication was executed in this batch.

## Verification and limits

- R46 publisher preparation, predecessor authority, embedded Owner reader and release transaction selection: **17 passed**. Python compilation, staged-content checks and `git diff --check` passed.
- Two existing `test_v4_native_membership_reference.py` cases call the real PG append path. Both stopped with `V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK`; no fake DSN was provided and no database write occurred. In a separate earlier selection, the other 19 tests passed.
- No daily build, PG connection, Head update, service startup, source acquisition or business acceptance was performed. Current accepted Head lacks the newly prepared predecessor and daily evidence authorities. Live PG append/readback remains unavailable.

## Accounting

Original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source). Formal completion remains **0 / 266**, remaining **266 / 266**. The matrix remains **33 code-level PG paths pending reconciliation**, **225 OPEN**, **8 ingress adapters open**, and **22 unmapped reference edges**. R46 wires producers for existing paths; it closes no additional formal baseline row.

## Next stage

Continue wiring other authorized candidate producers to the PG authority coordinator, then add a byte-preserving PG artifact contract for the period history/verifier without loading or rewriting the production artifact during this code-only work. Live publication and acceptance still require the approved PG writer and same-T0 Head readback.
