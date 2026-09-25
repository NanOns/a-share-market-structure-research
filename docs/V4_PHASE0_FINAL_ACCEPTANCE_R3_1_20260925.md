# V4 Phase 0 External Audit Repair R3.1 — Final Acceptance

## Decision

- **Phase 0:** `DEGRADED_PASS` after the owner-bound gate evaluated all eight stage records.
- **Local V4-01 entry gate:** `AUTHORIZED` for accepted RAW Bootstrap evidence. The R3.1 instruction still requires external audit confirmation before starting V4-01; no V4-01 work was started.
- **Scanner:** `NOT_APPLICABLE_UNTIL_V4_05`.
- **Core blockers:** none.
- **Remaining scoped limitations:** historic PIT/RAW import transfers to V4-01; adjusted empirical coverage is fail-closed; BaoStock remains optional; marked-relative consumer remains blocked; non-numeric policy parameter values are deferred to a separate versioned policy contract, so 00G is `DEGRADED_PASS`.
- **R3.1 audit card SHA-256:** `426b120f40759a908b32f608902ad5c0c90ce92268463b040057f5226247da06`.
- **Governing technical contract:** `DA-MSR-V4.2.2-CODEX-REV2`, SHA-256 `744b75906d932d6b11e01a1cd90f6a8de219642620dd30fd`.

## P0-A — Prior accepted state is frozen

Migration 008 renames the ambiguous prior digest to `prior_session_state_logical_digest`, requires an explicit prior `state_head_id`, and binds every publication head to its state-head identity and logical digest. The database now validates that a prior publication is the accepted head for the immediate previous market session and that its state head and digest match that head. Same-day revisions must preserve the complete prior identity tuple. Gaps fail when the previous session has an accepted head; initial-boundary gaps are accepted only at the beginning of the declared calendar. Publication-head changes are rejected after a next-session publication freezes that head. Migration 009 preserves the same guard semantics with unambiguous PL/pgSQL aliases.

Database tests cover unaccepted or non-head prior publications, namespace/head mismatch, a state head belonging to another publication, logical digest mismatch, same-day changes to each frozen prior field and gap, a false gap despite an accepted head, and mutation of a frozen prior publication head. A missing prior accepted head in a real previous market session remains representable as a scoped gap.

## P0-B — Phase 0 gate is owner-bound

`A_STOCK_TDX_SOURCE` is accepted only from 00D, `LIFECYCLE_SCHEMA` only from 00B, and `PUBLICATION_IDENTITY` only from 00C. RAW Bootstrap is derived from accepted statuses across all required Phase 0 stages, those owner-bound scopes, and the RAW capability at 00E. A stage's self-declared RAW capability cannot grant permission. Any `BLOCKED` stage blocks Phase 0 even when `blocks_v4_01` is false. A blocked non-entry capability must be represented by `DEGRADED_PASS`.

## P1-A — Non-numeric parameter policy boundary

The numeric registry remains limited to finite numbers or null. `quality_enum_by_capability` and `quality_to_consumer_matrix` values stay unassigned and fail-closed; before assigning values, they require a separately versioned policy contract. This scoped limitation is declared and validated in the algorithm framework, and 00G is `DEGRADED_PASS`; RAW Bootstrap remains independently eligible.

## Physical backup audit fact

The PostgreSQL physical backup was explicitly requested by the user and verified before deletion of the old database. It remains recorded as an informational deletion safety measure, not a V4 migration input or Phase 0/V4-01 prerequisite. No historical data was restored.

## Final schema and evidence

- Stage results: `00A FULL_PASS`, `00B DEGRADED_PASS`, `00C FULL_PASS`, `00D FULL_PASS`, `00E DEGRADED_PASS`, `00F DEGRADED_PASS`, `00G DEGRADED_PASS` for the declared non-numeric policy limitation, `00H DEGRADED_PASS`.
- PostgreSQL schema: 15 V4 tables, 25 validated foreign keys, zero unvalidated foreign keys, zero V4 runtime rows; migrations 001–009 are hash-checked and applied.
- Full Phase 0 suite: 63 passed in 1.88 s, recorded in `reports/v4_phase0/V4_PHASE0_R3_TEST_RECEIPT.json`.
- Owner-bound stage receipts and final machine gate: `reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R3.json` and `reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json`.
- No TDX input was modified, no 00D overlap was rerun, and V4-01/scanner implementation was not started.

The existing performance and A_STOCK acceptance evidence remain the R2 evidence; this repair did not rerun or replace their source measurements.
