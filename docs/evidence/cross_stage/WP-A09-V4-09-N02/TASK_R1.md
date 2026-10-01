# WP-A09-V4-09-N02 formal work package

Authority: V4_CROSS_STAGE_INDEPENDENT_AUDIT_REMEDIATION_MASTER_TASK_R1_20261001.md; scope and requirements remain the corresponding A-item, not a replacement formula.

Audit: AUD-V4-09-DB-CONSUMER-IDENTITY-N02. Priority: P2. Owner: src/v4/stock_prewatch_persistence.py.

Implementation plan: New unused migration (024 reserved for V4-10 R1.2); old rows/readback, immutable consumer identity, collision/revision rejection and exact rollback. Preserve historical 021.

Dependencies: accepted baseline only. Does not block unrelated engineering stages.

Engineering contract/schema/synthetic replay can proceed immediately. Real observation accumulation required: False; no estimate of days and no wait before unrelated development.

Acceptance: independent scope evidence, clean regression, candidate closure, then STOP for independent external audit. OPEN capabilities remain unavailable to production; no production/shadow/Focus permission. Preserve accepted heads, source roots, old artifacts and migrations.
