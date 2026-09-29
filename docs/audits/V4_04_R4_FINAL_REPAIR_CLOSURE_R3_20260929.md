# V4-04 R4 final external-audit repair — R3 candidate closure

## Stage identity and acceptance

- Starting HEAD: `1af58725b8c486904ed5149b6427739b9f2b051f`.
- Ending implementation HEAD: `e23d75012f319c6bd0c8b19d0f8f9e59cddf61c3`.
- Authority: `AGENTS.md`, REV2 executable contract, accepted V4-00–V4-03 heads, R2/R3 V4-04 tasks, and the R4 external audit task.
- Terminal status: `V4_04_FULL_PASS_CANDIDATE_R3`. This is a staging candidate pending independent external acceptance.
- Next stage: external acceptance audit of R3. V4-05 remains `NOT_STARTED / NOT_AUTHORIZED`; no V4-04 Accepted Head was created.

## Finding dispositions

| Finding | Repair | Evidence | Result |
| --- | --- | --- | --- |
| F01 unknown technical-window gap | One reusable validator checks accepted status rows against the complete session calendar and actual-bar identities. MA10, prior20 liquidity and pos250 fail closed on UNKNOWN or missing status; confirmed suspension is skipped. | Seven scenarios for both MA10 and liquidity, plus source-window checks in the R3 postcheck: 21 MA10, 21 liquidity, 19 pos250 samples. | PASS |
| F02 machine vector/branch coverage | Golden vectors independently execute every formal rule and meaningful branch, thresholds and UNKNOWN paths. The receipt is regenerated and hash-checked by the postcheck. | 18/18 rules; 70 branch positions; 77 threshold vectors; 26 UNKNOWN vectors; `rules_missing_vector_coverage=[]`. | PASS |
| F03 direct ATR source recomputation | R3 postcheck reads accepted QFQ daily close and accepted V4-03 MA20, ATR20 and prior_high20, then recomputes both derived values without using candidate state evidence as oracle. | `bias20_atr=21`, `dist_high20_atr=21` positive direct source sample checks. | PASS |

## Candidate, tests and preservation

- R3 artifact: `reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R3.jsonl.gz`.
- R3 SHA256: `0c0fccd06fd2c2bad856b529d3ae2bcf64584f451e97961380997d72830b46b6`, identical in both builds.
- Required-scope rows: 5,222 unique securities; SH_MAIN 1,702, SZ_MAIN 1,494, CHINEXT 1,408, STAR 618.
- Profile quality: 4,981 COMPLETE, 241 PARTIAL_UNKNOWN.
- Independent postcheck: PASS, all 5,222 rows; direct source recompute counts: MA10 21, minimum_liquidity 21, pos250 19, bias20_atr 21, dist_high20_atr 21, weekly 20, monthly 22.
- Focused runtime gate: `python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q`; 374 passed, 2 skipped, 0 failed. The R3 runtime receipt binds command, implementation commit, source hashes and timestamps.
- R1 historical artifact remains SHA256 `afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07`.
- R2 historical artifact remains SHA256 `89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12`.
- The repository-wide pytest collection issue remains open as a separate cross-cutting audit item under `docs/audits/V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1_20260929.md`.

The R3 stage manifest binds the R3 artifact and all versioned receipts. Accepted upstream artifacts and TDX roots were not modified.
