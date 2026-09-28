# V4-03 algorithm AST expressiveness audit R1

Scope: machine-contract conformance for V4-03 rolling MA, population standard deviation, rank midrank, and historical equal-weight aggregation. This is a separate cross-cutting audit item under project guardrail 8; it does not modify V4-00G.

Evidence: `config/v4_algorithm_contract_framework_v1.json` version 1.1.0 and executable validator `src/v4/contracts/algorithm_contract.py` allow only `AND`, `OR`, `NOT`, `COMPARE`, `ARITHMETIC`, `FIELD_REF`, `PARAM_REF`, `ENUM_LITERAL`, and `MATH_LITERAL`. The arithmetic operators are `ADD`, `SUB`, `MUL`, `DIV`, `MIN`, `MAX`. There is no window aggregate, population standard deviation, log, midrank, or set-mean node. A `FIELD_REF` of a precomputed value would not serialize the algorithm and would violate the task’s independent machine contract requirement.

Current status before R1 repair: **OPEN / MACHINE_AST_INSUFFICIENT_FOR_REQUIRED_ALGORITHMS**. V4-03 may continue pure implementation and diagnostic vectors, but no per-algorithm contract or final internal acceptance can be claimed by encoding incomplete or circular ASTs.

Acceptance condition: an authorized versioned extension or explicitly approved operator encoding that represents every required formula and window binding without circular producer inputs; update validator and independent positive/negative vectors; then validate each V4-03 algorithm contract. This audit acceptance is independent from the V4-03 stage gate.

## V4-03 External Acceptance R1 repair disposition (2026-09-28)

Implementation response:

- Preserved the original `config/v4_algorithm_contract_framework_v1.json` V1.1 contract and validator unchanged.
- Added `config/v4_algorithm_contract_framework_v1_2_0.json` as a scoped corrective extension with `RULE_AST_V2`, prior-only lag, typed window aggregation/rank, log/return transforms, cross-section ranking/aggregation, and explicit field-local quality references.
- Added `src/v4/contracts/algorithm_contract_v12.py` and positive/negative vectors. The 47 stock/relative field contracts are serialized individually and bind the exact extension file SHA-256.
- `pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py`: 37 passed. The generated 47 contracts validate; every serialized contract is also subjected to an undeclared-field negative validation vector.

Disposition: **CORRECTIVE IMPLEMENTATION COMPLETE / EXTERNAL AUDIT PENDING**. This closes the implementation portion of this audit item, not its external acceptance. The independent V4-03 stage gate remains blocked by separately listed sector-input and full-history requirements; see `docs/evidence/V4_03_EXTERNAL_ACCEPTANCE_R1_REPAIR_DISPOSITION_20260928.md`.

## R2 numeric execution follow-up (2026-09-28)

The external R1 audit found that structural AST validation did not execute the 47 contracts numerically. R2 adds an independent `RULE_AST_V2` interpreter and a fixed synthetic fixture. All 47 version 1.1.0 contracts now execute one observed and one unknown-input vector (94 total); the receipt is `reports/v4_03/V4_03_AST_NUMERIC_VECTOR_ACCEPTANCE_R2.json`. Negative tests reject a changed expected value and an omitted negative case. This addresses the implementation defect, while external acceptance of the audit item remains pending. The V4-03 stage gate remains blocked independently.
