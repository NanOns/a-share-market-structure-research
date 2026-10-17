---
stage_id: V4_R21_R4_DM01_DATA_HEAD_V2_PG_IMPORT_R97_20261017
branch: codex/v4-workspace-cleanup
status: EXACT_V2_HEAD_IMPORTER_AND_PG_CONSUMER_COMPATIBILITY_READY_LIVE_IMPORT_OPEN
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
---

# R97: V4 DM-01 accepted Data Head V2 import and consumer compatibility

## Scope

Reviewed the formal R21-R4 execution card and the R96 Data Head PG consumer report. Fixed the concrete V1/V2 contract mismatch: the current accepted V4 Data Head is `V4_DATA_ACCEPTED_HEAD_V2` 2.0.0, while the continuous-maintenance PG caller still required V1.

Added an explicit one-time import payload builder and `scripts/import_v4_dm01_data_head_to_pg.py`. The builder requires the exact current Data Head namespace, validates its path/byte count/SHA against the active V4.15 `CurrentStageAuthority`, and preserves both decoded Head fields and original UTF-8 bytes in a versioned envelope. The CLI defaults to dry-run; PG append requires explicit `--write` plus the existing explicitly configured V4 writer. Runtime readback verifies the exact embedded bytes, accepted authority bindings, V2 identity, scope, and date before using the Head; it does not fall back to a local Head. The report/receipt Head SHA now denotes the preserved raw Head SHA.

## Verification

- Focused V4 DM-01 state, daily consumer, and PG progress selection: **28 passed**.
- The import CLI dry-run was executed against the current repository Head and current accepted V4.15 Authority: **VALIDATED_DRY_RUN**, trade date `2026-09-30`, 16,890 source bytes, SHA-256 `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`.
- The first pytest collection attempt failed before tests because the global Python lacked a working psycopg PQ implementation. Reran with repository test dependencies from `G:/codex_tmp`; no global Python package was changed.
- No PG connection, DML, DDL, Head CAS, service start, or production publication occurred. The importer is prepared but has not been written to PG.

## Original stable-callsite accounting

This batch establishes a real V4 import-to-PG-stage-state path and fixes its runtime V2 consumer contract. The exact R20/R21 baseline has no reconciled stable ID for this newly wired runner/import pair, and the separate current-stage-authority file reader remains open. Therefore no original ID is closed: **0 / 266 formally complete; 266 / 266 remaining**. The existing matrix totals are not altered. Live PG readback, per-ID reconciliation, and business acceptance remain open.

## Next

Continue the remaining V4 Head/Authority/descriptor/daily/BFF and Owner consumer batches, reconcile exact stable IDs, and run the explicitly approved live read path when a compliant PG Reader is available. Do not run the importer with `--write` absent separate authorization for PG DML.
