# V4-03 algorithm AST expressiveness audit R1

Scope: machine-contract conformance for V4-03 rolling MA, population standard deviation, rank midrank, and historical equal-weight aggregation. This is a separate cross-cutting audit item under project guardrail 8; it does not modify V4-00G.

Evidence: `config/v4_algorithm_contract_framework_v1.json` version 1.1.0 and executable validator `src/v4/contracts/algorithm_contract.py` allow only `AND`, `OR`, `NOT`, `COMPARE`, `ARITHMETIC`, `FIELD_REF`, `PARAM_REF`, `ENUM_LITERAL`, and `MATH_LITERAL`. The arithmetic operators are `ADD`, `SUB`, `MUL`, `DIV`, `MIN`, `MAX`. There is no window aggregate, population standard deviation, log, midrank, or set-mean node. A `FIELD_REF` of a precomputed value would not serialize the algorithm and would violate the task’s independent machine contract requirement.

Current status: **OPEN / MACHINE_AST_INSUFFICIENT_FOR_REQUIRED_ALGORITHMS**. V4-03 may continue pure implementation and diagnostic vectors, but no per-algorithm contract or final internal acceptance can be claimed by encoding incomplete or circular ASTs.

Acceptance condition: an authorized versioned extension or explicitly approved operator encoding that represents every required formula and window binding without circular producer inputs; update validator and independent positive/negative vectors; then validate each V4-03 algorithm contract. This audit acceptance is independent from the V4-03 stage gate.
