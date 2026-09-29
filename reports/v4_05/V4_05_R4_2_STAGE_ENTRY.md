# V4-05 R4.2 Stage Entry

## Contract and scope

- Contract: `V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING`.
- Starting HEAD: `f1e3d2ee4721e4880c043e8ca949e7c1e47dce41`.
- Implementation commit: `1a88fcba876e619e45584964cc11fde48b1883f8`.
- Governing task: `docs/evidence/V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING_TASK_20260929.md`.
- Latest R4.1 external audit: `docs/evidence/V4_05_REPLAY_GATE_A_R4_1_EXTERNAL_AUDIT_20260929.md`.
- Sole scope: close `POSTGRES_LEDGER_TESTED_R4_NOT_R4_1_EXACT_IDENTITY`; R4.1 business artifacts and B05 remain frozen.

## Exact binding results

- R4.1 candidate manifest: `reports/v4_05/V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json`; SHA-256 `e4adabedbd3a5fec62fcd251facdad3f47bf6a79eac0e09256f62bcd5d0cfe5f`.
- PostgreSQL ledger binds Core Profile `9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`, Factors `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`, Period `e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233`, and the canonical R4.1 Market Reference identity.
- Actual state and publication head logical digest: `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`.
- `all_exact_bindings_match=true`; `old_r4_binding_count=0`.

## Runtime and acceptance

- Fresh pushed-commit clone: `PASS`; exact binding test `..                                                                       [100%]
2 passed in 0.84s`.
- Formal PostgreSQL 18.6, 12 migrations, isolated connection; I01–I05 passed, production connection used: `false`.
- Full suite: `428 passed, 2 skipped in 6.69s`; PostgreSQL schema tests ran; skipped test names/reasons appear in `V4_05_R4_2_RUNTIME_TEST_RECEIPT.json`.
- R4 business drift remains zero; 5,222 target identities and `trend_axis=UNKNOWN`.
- Candidate state: `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2`; external acceptance remains `PENDING`.
- No V4-05 Accepted Head was created; protected heads are unchanged; V4-06/V4-07 remain unauthorized.
- Next stage: `INDEPENDENT_EXTERNAL_AUDIT_R4_2`.
