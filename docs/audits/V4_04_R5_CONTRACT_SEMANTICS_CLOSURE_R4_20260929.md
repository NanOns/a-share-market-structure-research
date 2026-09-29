# V4-04 R5 contract-semantics repair — R4 candidate closure

## Stage identity

- Starting HEAD: `0915c9692791f8482d799ae671513e8b1a1ea5b3`.
- Ending implementation HEAD: `044dc637f90b35c6097bb800b1d4d755fdfb792c`.
- Authority: `AGENTS.md`, REV2 executable contract, accepted V4-00–V4-03 heads, applicable V4-04 task cards and the R5 external audit task.
- Terminal stage status: `V4_04_FULL_PASS_CANDIDATE_R4`; external acceptance remains pending.
- Next stage: independent external audit of R4. V4-05 remains `NOT_STARTED / NOT_AUTHORIZED`, with no V4-04 Accepted Head promotion.

## Finding dispositions

| Finding | Repair and evidence | Result |
| --- | --- | --- |
| S01 minimum_liquidity hidden dependency | Removed the `amount_ratio20` availability gate. Tests prove valid prior20 amount yields true or false while amount_ratio20 is UNKNOWN and compression remains UNKNOWN. Independent source audit found 21 evaluable sampled windows and 0 false UNKNOWN. This full-market sample had 0 rows where amount_ratio20 was UNKNOWN and liquidity was independently evaluable; the fixture covers that case. | PASS |
| S02 enum UNKNOWN machine semantics | Versioned V3 AST declares required fields and enum dependencies; versioned R4 executor propagates UNKNOWN for Relative and severe_extension. Vectors cover both Relative dependencies, severe_extension, participation CLV, trend damage, last-known regime and interrupted hysteresis. | PASS |
| S03 inclusive drawdown boundaries | Production and independent machine compare price ratio with `1 +` the registered negative threshold, encoded with ADD in the V3 AST. Exact -5% is SHALLOW and exact -15% is MODERATE for N=20 and N=60. | PASS |

## Machine and full-market gates

- Machine vectors: 18/18 rules, 70 branch positions, 78 threshold vectors, 32 UNKNOWN vectors; 2 branch-specific UNKNOWN, 3 enum UNKNOWN, 2 stateful hysteresis and 2 inclusive-boundary vectors. Semantic coverage status PASS; missing rule coverage `[]`.
- R4 artifact: `reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz`.
- SHA256: `b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52`, identical across two builds.
- 5,222 unique required-scope rows: SH_MAIN 1,702; SZ_MAIN 1,494; CHINEXT 1,408; STAR 618.
- Independent postcheck: PASS, all rows; 36 deterministic source samples; direct source recompute counts include MA10 22, minimum_liquidity 21, pos250 19, bias20_atr 21, dist_high20_atr 21, weekly 21 and monthly 23.
- Focused runtime gate: `python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q`; 390 passed, 2 skipped, 0 failed. The R4 receipt binds the command, implementation commit, test hashes and runtime timestamps.

## Historical preservation

- R1 SHA256: `afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07`.
- R2 SHA256: `89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12`.
- R3 SHA256: `0c0fccd06fd2c2bad856b529d3ae2bcf64584f451e97961380997d72830b46b6`.
- R1/R2/R3 artifacts and receipts were not rewritten. Accepted upstream artifacts and TDX roots were not modified.
- The repository-wide pytest collection issue remains open under `docs/audits/V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1_20260929.md` as a separate cross-cutting audit item.

The R4 stage manifest binds the candidate artifact, source and contract digests, semantic machine receipt, independent postcheck, focused test runtime and all versioned stage evidence.
