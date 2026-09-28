# V4-03 External Acceptance R1 Repair Disposition

- Date: 2026-09-28
- Repository branch: `codex/v4-system-reform`
- Frozen input: `V4_DEV_BASELINE_HEAD @ 2026-09-24`
- Governing stage card: `V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_R2_20260928.md`
- Latest external review: `V4_03_EXTERNAL_ACCEPTANCE_R1_20260928.md`
- Result: **REPAIR_IMPLEMENTATION_COMPLETE_STAGE_ACCEPTANCE_BLOCKED**

## Repairs and evidence

| Finding | Disposition | Evidence |
|---|---|---|
| B01 | Versioned RULE_AST_V2 extension; 47 individual field contracts validated; V1.1 compatibility tests retained. | `config/v4_algorithm_contract_framework_v1_2_0.json`, `config/v4_03_algorithm_contracts_v1.json` |
| B02 | Symmetric STRONG/WEAK erratum is versioned and has boundary vectors. | `config/v4_03_market_regime_trend_amendment_v1.json`, `docs/evidence/V4_03_MARKET_REGIME_TREND_WEAK_ERRATUM_R1_20260928.md` |
| C01 | Prior extrema and technical windows now tolerate suspended T0 where current price is not an input; `pos60` preserves current-bar unavailability. | `src/v4/factors/core.py`, core vectors |
| C02 | 47 field schema validates against the V4-00G output metadata contract and binds the extension digest. | `config/v4_03_output_schema_v1.json` |
| C03 | 5,222 x 47 diagnostic candidate; independent formula/quality replay has 0 mismatches. | `reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R1.json`, `reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R1.json` |
| C04 | Relative values bind PIT current/start snapshots, session, adjustment set, source digest, prior RPS artifact and quality. | `src/v4/factors/relative.py`, full-scope artifact |
| C05 | Native contracts and PIT market path registry exist. Accepted sector membership is absent, so full-market sector materialization is blocked. | `config/v4_03_native_contract_registry_v1.json`, `config/v4_03_native_scope_map_v1.json` |
| C06 | Sector metrics use separate quote, amount, ret1 and MA20 field-local evaluability sets, each with output identity/digest. | `src/v4/factors/native.py`, sector vectors |
| C07 | A missing daily return makes the same path version suffix UNKNOWN; 200 rows independently match. | market path candidate and independent postcheck |

## Stage record

- Contract: V4-03 Pure-Core Factors only; V4-04 profile states, scanner, trading and V4-08 qualification remain outside scope.
- Evidence: 37 V4-03/V1.1-compatibility tests pass; full diagnostic 5,222 securities; 47 fields; 200-session market path; independent 47-field and path postchecks pass; four deterministic artifacts replay byte-identically.
- Performance facts: core, full-scope and market-path run times, CPU, sampled peak RSS, OS peak working set, hardware and cache-state limitation are recorded in `reports/v4_03/V4_03_PERFORMANCE_MEASUREMENT_R1.json`.
- Acceptance: **V4-03 internal acceptance is not granted.** Artifacts remain `DIAGNOSTIC_NON_PIT`; full-history replay, byte-level regeneration of each field identity digest, full-market regime primitives and sector materialization remain open. The frozen V4-02 manifest exposes 0 sector-membership components.
- Safety counts: scanner 0; trading 0; TDX-root writes 0; V4-02 head mutations 0; stage-head mutations 0; DEV-baseline mutations 0.
- Final-stage receipt: not generated because required gates remain open. V4-04 remains blocked.
- Next stage: establish an accepted PIT sector-membership input, then complete full-history native market/sector materialization and independent identity-digest regeneration. Keep V4-04 stopped.

The machine disposition is `reports/v4_03/V4_03_EXTERNAL_ACCEPTANCE_R1_REPAIR_DISPOSITION_20260928.json`. This is a repair response for external review, not an external acceptance claim.
