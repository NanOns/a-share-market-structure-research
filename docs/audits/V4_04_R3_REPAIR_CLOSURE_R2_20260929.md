# V4-04 R3 external audit repair — R2 candidate closure

## Authority and scope

- Starting HEAD: `ace30af36ce5440bb989312fce3e4385e8f8e6e6`.
- R2 implementation HEAD: `c833c8119293beb6f213241b5296ff0919399faa`.
- Governing authorities: `AGENTS.md`, REV2 executable contract, V4-04 R2 task, R3 external audit task, and accepted V4-00–V4-03 heads.
- Terminal stage result: `V4_04_FULL_PASS_CANDIDATE_R2` (candidate only; external acceptance still pending).
- Next stage: independent external audit of R2. V4-05 remains `NOT_STARTED`; no V4-04 Accepted Head has been promoted.

## Finding dispositions

| Finding | Repair and evidence | Result |
| --- | --- | --- |
| B01 machine AST | Independent interpreter supports every declared operator and 18 registered rule paths. R2 postcheck records coverage 1.0, no unsupported operator, no unexecuted rule. | PASS |
| B02 producer identity | V2 registry identifies `profile_primitives` as producer for `bias20_atr`, `dist_high20_atr`, and `pos250`. Each registered field is matched to the R2 artifact envelope, producer contract, parameter set, and schema requirement. | PASS |
| B03 window lineage | R2 rows bind the accepted V4-03 mapping SHA256, the V4-04 mapping SHA256, accepted primitive window metadata, derived field windows, and CLOSED_ONLY period lineage. The verifier checks source mapping, all row envelopes, and sampled closed-period source windows. | PASS |
| B04 MA10 | Removed the undeclared MA20 dependency. A 15-bar QFQ fixture with MA20 UNKNOWN yields MA10 OBSERVED; the independent postcheck recomputes MA10 from accepted daily source. | PASS |
| Component status | V2 output schema freezes READY/PARTIAL/UNKNOWN_DATA/DEGRADED mapping; unit tests and independent row checks cover it. | PASS |

## Artifact and gates

- R2 candidate: `reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R2.jsonl.gz`.
- SHA256: `89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12` on both deterministic builds.
- Rows: 5,222, unique required-scope securities. SH_MAIN 1,702; SZ_MAIN 1,494; CHINEXT 1,408; STAR 618.
- Profile quality: 4,981 COMPLETE; 241 PARTIAL_UNKNOWN.
- Independent postcheck: PASS, 5,222 rows, 18/18 machine rules, 27 source samples. Registry consistency and window traceability receipts: PASS.
- Focused runtime gate: `python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q`; 366 passed, 2 skipped, 0 failed. Runtime log and test source hashes bind the implementation commit.
- Historical R1 artifact remains SHA256 `afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07`; no R1 file was overwritten.
- The repository-wide pytest collection issue remains open under `V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1_20260929.md` and is outside this stage gate.

## Changes

New R2 algorithm, registry, schema, and field-window contracts; R2 builder, independent executor, verifier, and sealer; `profile_primitives` MA10 and window metadata repair; component status mapping; regression fixtures and R2 receipts. No accepted upstream artifact or TDX source was modified.

## Acceptance boundary

This is an internally sealed R2 candidate. External acceptance has not yet been recorded. V4-05 remains unauthorized until that acceptance.
