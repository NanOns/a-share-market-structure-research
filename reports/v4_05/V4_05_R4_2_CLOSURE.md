# V4-05 R4.2 Exact Ledger Binding Candidate

Stage: `V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING`

Candidate: `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2`

Exact candidate binding: `PASS`

External acceptance: `PENDING`

## R4.1 identity is now what G08 tested

- Candidate manifest `reports/v4_05/V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json` SHA-256: `e4adabedbd3a5fec62fcd251facdad3f47bf6a79eac0e09256f62bcd5d0cfe5f`.
- Core Profile artifact SHA `9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`; logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`.
- Full Scope Factors artifact SHA `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`; logical digest `0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2`.
- Period artifact SHA `e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233`.
- Market Reference one-session output digest `80d8ac5cc69e8ae4d165f89324e45d0cc7e49a81d13339b31ff8fbec5e578554`; ledger source digest uses canonical R4.1 JSON identity.
- PostgreSQL consumed-source evidence reports `old_r4_binding_count=0` and `all_exact_bindings_match=true`.
- State head and publication head both bind Core Profile logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`.

## Regression and runtime

An automated regression test asserts that the G08 baseline source manifest refers only to R4.1 receipts/artifacts. A fresh clone of `1a88fcba876e619e45584964cc11fde48b1883f8` restored the required R4.1 LFS artifacts, passed the exact-binding test, ran PostgreSQL 18.6 with 12 formal migrations and I01–I05, and completed the required pytest suite: `428 passed, 2 skipped in 6.69s`.

## Candidate boundary

R4.1 business values and B05 remain frozen. The current forward capability remains `DEGRADED_PASS`; historical as-recorded adjusted price remains blocked for missing first-availability evidence. No V4-05 Accepted Head was created or modified, and V4-06/V4-07 were not started. The next stage is independent external audit for R4.2.

See `V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json`, `V4_05_R4_2_RUNTIME_TEST_RECEIPT.json`, `V4_05_R4_2_CLEAN_CHECKOUT_RUNTIME.json`, and `V4_05_R4_2_INDEPENDENT_POSTCHECK.json` for detailed evidence.
