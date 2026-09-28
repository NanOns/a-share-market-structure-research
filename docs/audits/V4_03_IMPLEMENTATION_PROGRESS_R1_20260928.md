# V4-03 implementation progress R1 — 2026-09-28

| Item | Result |
|---|---|
| Stage contract | DA-MSR-V4.2.2-CODEX-REV2 §10A0, §49A.1, §78, §87A; V4-03 R2 task; V4-00G window framework 1.1.0 |
| Frozen input | `data/v4/V4_DEV_BASELINE_HEAD.json`, cutoff 2026-09-24; SHA-256 `45695460b0147c6ada12e0ebd8e5070ac0a45eebea26603ff5a3daddc4dd5094` |
| Phase 0 | `FULL_PASS` in `data/v4/V4_STAGE_ACCEPTED_HEAD.json` |
| Gate 03-A0 | Legacy difference register created; no legacy factor helper imported |
| Gate 03-A | Field scope map and 47-row field metadata registry drafted; per-algorithm machine contract and registry validation pending |
| Gate 03-B | Technical/cross-section/forward boundary mapping drafted; acceptance pending full vectors |
| Gate 03-C | 39 core stock fields implemented in isolated `src/v4/factors`; partial vectors and one real READY/one unsupported sample; acceptance pending all required vectors and full-market run |
| Gate 03-D | RPS midrank, start-universe market reference, relative fields and deltas implemented as pure functions; PIT identity and full historical recomputation pending |
| Gate 03-E | Market reference path and non-trend axes implemented; trend WEAK AST conflict independently open |
| Gate 03-F | Sector native unqualified numerators/denominators implemented; formal boundary receipt pending |
| Gate 03-G | 5,222-security required-scope core diagnostic completed; independent MA20 numerical recomputation of 5,024 OBSERVED rows had zero mismatch. Full 47-field run, all-field independent postcheck, formal performance evidence, accepted publication and final receipt remain open. |

Evidence: `tests/v4_03/test_core_vectors.py` passed 11 tests; real-data diagnostic `reports/v4_03/staging/V4_03_CORE_FACTOR_REAL_SAMPLE_SH600006_R1.json` has 39 OBSERVED fields; the SH.600000 unsupported-adjustment sample has 39 `ADJUSTMENT_UNKNOWN` fields. `reports/v4_03/V4_03_REAL_SAMPLE_INDEPENDENT_POSTCHECK_R1.json` independently verifies MA20, ret5 and vol20 for the READY sample. The real samples inherit `DIAGNOSTIC_NON_PIT`; they are not forward-observed evidence.

Required-scope cutoff diagnostic: `reports/v4_03/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_RECEIPT_R1.json` binds the frozen input digests, reports 1,035,434 adjusted daily rows consumed in a bounded 200-session window, 5,222 output securities (SH_MAIN 1,702; SZ_MAIN 1,494; CHINEXT 1,408; STAR 618), field quality and UNKNOWN reason distributions, and about 38 seconds elapsed. MA20 has 5,024 OBSERVED and 198 UNKNOWN; 176 of the UNKNOWN are adjustment-unsupported. `reports/v4_03/V4_03_CORE_REQUIRED_SCOPE_NUMERIC_POSTCHECK_R1.json` independently recomputes every OBSERVED MA20 value from the accepted parquet and finds zero mismatch. Two identical diagnostic runs produced the same artifact SHA-256 `d0982fbc0d0e2c8264e9e0e8ee027a2bd1d9d5b4773d8c0fc3639a657d144953`. This is a diagnostic core-only subset, not the required final full-market publication or all-field postcheck.

Acceptance result: **IMPLEMENTATION_IN_PROGRESS / FINAL_ACCEPTANCE_BLOCKED_BY_TWO_CONTRACT_AUDITS / NOT_V4_03_INTERNAL_PASS**. Tests and samples are insufficient for the R2 final gate. No V4-03 accepted artifact or final receipt was issued. `V4_DATA_ACCEPTED_HEAD`, `V4_DEV_BASELINE_HEAD`, `V4_02_ACCEPTED_HEAD` and `V4_STAGE_ACCEPTED_HEAD` remain untouched; no TDX-root write, BaoStock call, scanner run, V4-04 or V4-08 field publication occurred.

Next stage: resolve the separately tracked V4-00G AST expressiveness and trend WEAK contract conflicts; complete each family’s machine AST/schema/parameter identity and vectors; run frozen required-scope full market with independent recomputation and performance evidence. V4-04 remains blocked pending V4-03 external acceptance.
