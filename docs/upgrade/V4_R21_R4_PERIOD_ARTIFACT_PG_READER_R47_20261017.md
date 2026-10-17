---
stage_id: V4_R21_R4_PERIOD_ARTIFACT_PG_READER_R47_20261017
branch: codex/v4-workspace-cleanup
status: PERIOD_HISTORY_AND_VERIFIER_CHUNKED_PG_PATH_CONNECTED_PENDING_LIVE_READBACK
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 33
ingress_adapters_open: 8
other_callsite_rows_open: 225
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_WRITE_DSN
next_stage: continue remaining business Owner and other-business callsites; run exact daily publication only after approved PG writer is configured
---

# V4 R21-R4 period artifact PG reader

Date: 2026-10-17 (Asia/Shanghai). R44 daily evidence and R46 publisher preparation code were reviewed before adding the nested period artifact path. The accepted local Head points at a 67,380,907-byte compressed input history and a 3,116-byte verifier source; only their binding metadata was inspected in this batch.

## Implemented

- Added `V4_OPERATIONAL_PERIOD_ARTIFACT_PG_R1` for the exact `input_history` and `verifier` artifacts referenced by the period numeric oracle.
- The writer reads each artifact in bounded 1 MiB chunks, stores each chunk as an immutable append-only PG fact, and embeds inline PG descriptors, chunk order, byte counts and SHA-256 values under `native_period_artifacts`.
- The publisher's exact-daily preparation step now includes this artifact authority after daily evidence is bound. `OperationalSuccessorV1.validate()` uses the PG artifact attestor when that authority is present; the attestor reads every chunk and verifies chunk hashes, total byte count and the exact original full-file SHA-256 without opening the source artifact. Legacy candidates without the authority retain the checked-file ingress path.
- This extends an existing daily validation route; no additional original 266-row baseline item is marked formally complete in R47.

## Verification and limits

- Period artifact, daily evidence, predecessor, publication preparation and transaction tests: **13 passed**. Tests use small temporary byte strings and controlled Owner-store boundaries to check chunk encoding, order, digest and no-file-fallback behavior; they are unit verification, not business acceptance.
- Python compilation and `git diff --check` passed. No 67 MB source file was copied, no PG connection or write occurred, and no Head or pointer changed.
- The live accepted Head has not yet received `native_period_artifacts`; the production PG writer is not configured. Full PG write/readback and same-T0 business validation remain open.

## Accounting

Original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source). Formal completion remains **0 / 266**, remaining **266 / 266**. The current inventory remains **33 code-level PG paths pending reconciliation**, **225 OPEN**, **8 ingress adapters open**, and **22 unmapped reference edges**. No formal baseline row closes in this batch.

## Next stage

Continue the remaining Owner and other-business read callsites in bounded groups. Live validation of this byte path requires the explicitly configured PG writer and an accepted Head carrying the new authority.
