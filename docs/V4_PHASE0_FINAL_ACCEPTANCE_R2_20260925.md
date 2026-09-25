# V4 Phase 0 Final Acceptance — R2 Repair — 2026-09-25

## Decision

- **Phase 0:** `DEGRADED_PASS`
- **V4-01 entry:** `AUTHORIZED` for accepted RAW Bootstrap scopes, subject to external audit confirmation required by R2.
- **Scanner:** `NOT_APPLICABLE_UNTIL_V4_05`
- **Remaining Phase 0 blockers:** `NONE`
- **Repair card SHA-256:** `f51e71ec8a3c02a5551bf07f66366856cf146182a76729b549871a680dcd0fe0`
- **V4.2.2 CODEX REV2 SHA-256:** `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`
- **Base final executable contract SHA-256:** `ac86f92f9cfaa3547a0ba99959e749da02f0fa7f9c0a1568ad95627db0200b97`
- **Test result:** 42 passed in 1.06 s on the final post-migration run.

## Scope-level gate

Required V4-01 scopes `RAW_BOOTSTRAP`, `A_STOCK_TDX_SOURCE`, `LIFECYCLE_SCHEMA`, and `PUBLICATION_IDENTITY` are explicitly accepted. `MARKED_RELATIVE_BENCHMARK_CONSUMER` remains blocked because representative coverage/quote-age thresholds and the quality-consumer matrix are unset. This scoped block does not block RAW Bootstrap.

## Stage results

| Stage | Result | R2 repair / limit |
|---|---|---|
| 00A | FULL_PASS | Clean baseline remains; no second reset. Physical backup is informational, not an acceptance prerequisite. |
| 00B | DEGRADED_PASS | Lifecycle and PIT facts are now schema-backed; historical PIT data remains for V4-01. |
| 00C | FULL_PASS | Unique publication ID per physical revision, explicit lineage, parent chain, session calendar and digest constraints. |
| 00D | FULL_PASS | Previously accepted A_STOCK source gate retained; no package download or overlap rerun. |
| 00E | DEGRADED_PASS | Unsupported adjusted categories fail closed; RAW allowed. |
| 00F | DEGRADED_PASS | BaoStock remains optional. |
| 00G | FULL_PASS | Framework, registry, AST operators/arity, enum identity, output and section schemas validate; negative vectors pass. |
| 00H | DEGRADED_PASS | Benchmark consumer remains scoped blocked; REV2 §74 measurements recorded where components exist; absent/unavailable metrics explicit. |

## Evidence

- PostgreSQL: 15 V4 tables, 24 validated foreign keys, zero unvalidated keys, zero runtime rows. Seven hash-checked migrations are applied; fresh schema rebuild took 1.02 s in a temporary database which was removed, and the non-template database set was verified unchanged.
- Publication/PIT schema and negative tests verify unique publication IDs, same-day parent rules, no forks, exact prior valid session/digest, lifecycle source timestamps, PIT revision chains, append-only corrections, and current membership is not historical proof.
- Performance: isolated fresh-schema rebuild, rollback-only 1,000-row PostgreSQL write/read, DB size delta, CPU/RAM and migration-ledger timing are reported. The legacy API/UI was not listening; V4 daily/factor/sector/Radar/Focus modules are not implemented; 00D runtime was not remeasured because R2 forbids rerunning it.
- Final repair migration 007 binds state heads to the unique publication ID and namespace and constrains namespace cutovers to an existing frozen source head.
- TDX root unchanged: `a0e219048f025a9b8fa5998a8a2108535e9cee4b9f8a25573adf1019e97831ff` before and after. A_STOCK remains `ACCEPTED_SOURCE_PACKAGE` with zero unexplained and zero identity mismatch rows.
- Physical backup: `PHYSICAL_BACKUP_VERIFIED`. It was explicitly requested in the prior conversation; R2's assertion that it was unrequested conflicts with that record. Backup is informational only and does not gate Phase 0.

## Transfers

Two-year RAW history and historic PIT membership transfer to V4-01; Adjusted Canonical empirical coverage to V4-01/02; INDEX residuals to an independent non-core source audit; optional BaoStock to a later explicitly enabled stage. Do not start V4-01 until the external audit specified by R2 confirms entry permission.

Canonical machine receipt: [`reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json`](../reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json). Stage ledger: [`reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R2.json`](../reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R2.json). Performance evidence: [`reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json`](../reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json).
