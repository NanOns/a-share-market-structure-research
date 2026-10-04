# R30R1 Native session status and owner binding repair

Baseline: `3f0663804bf104dd3e61e65d9927cb7f2081fa3b`. Exact tested source: `0d85127a838a00d42652981d2935b18f21b62e68`.

R30 used generic session statuses and omitted the accepted native slot owner. This repair binds the exact V4-16 Observation Slot V2 ID, file digest and native states. Shadow ACCEPTED_ON_TIME and MISSED_OBSERVATION_SLOT are distinct from projection_evaluable and its reason. Accepted-but-non-evaluable is retained as accepted native status, counts zero and resets streak without becoming missed. Alias/unknown states, wrong/missing owner binding, inconsistent count claims and missed-but-evaluable rows are rejected.

Observation receipt status is exact native status with separate projection fields. Production native authority remains FUTURE_ACCEPTED_BINDING_REQUIRED and real-gate evidence NOT_COUNTABLE. Future Production examples exist only in explicitly marked CONTRACT_DESIGN_SIMULATION fixtures with simulated binding; they grant no current authority.

F21-01/05/06 are normalized; remaining F21 semantics and all PASS_KEEP contract sections remain unchanged. Historical R30 reports/seal retain their original bytes and audit meaning; they are not rewritten to conceal the repair. No real writer, settlement engine, gate grant, Focus/UI route change or accepted head is created.

Local and clean regression: 346 tests, 343 passed, only the same three inherited R26-A01 failures, no errors/skips/deselections. Eight S21 negative cases and independent native-contract assertions pass. All other existing tracked files and unrelated work remain unchanged. Clean checkout/LFS proof uses F:/codex_tmp; tests/captures use E:/codex_tmp/test_temp.

Local repair is ready for independent external audit; implementation remains BLOCKED_WAIT_REAL_OBSERVATION and real continued Forward observation NOT_STARTED. NEXT = STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT. Push does not close the external P0 findings by itself.
