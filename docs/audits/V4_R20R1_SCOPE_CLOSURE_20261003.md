# R20R1 capability scope closure

Execution baseline: `7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9` on `codex/v4-system-reform`.
The R20R1 master is the scheduler; supplied audit/task cards are evidence and scoped requirements, not authorization for future promotion.

The independent feasibility oracle follows V4-14 Accepted Head → runtime seal → its exact publication allowlist, and compares accepted T0 with the accepted calendar/Data cutoff. Of 24 sealed publications, 23 are ENGINEERING_SYNTHETIC and the only real accepted-source publication is 2026-09-30. The Data Head ends on the same date. No genuinely accepted earlier real matured publication/enrollment lineage exists. Historical price rows and earlier engineering replay dates do not manufacture one.

R20's persisted real enrollment is RECONSTRUCTED_ASOF, with accepted Sept30 source bindings; it supports current T0 integration and pending due/readback, not historical PIT. All five real horizons are PENDING, have no numeric path outcomes, and the real accepted future endpoint count is zero. Mature numerical outcomes remain ENGINEERING_VECTORS_ONLY.

`reports/r20r1/V4_15_CAPABILITY_SCOPE_GATE.json` supersedes only the promotion meaning of R20's generic REAL_ACCEPTED_SOURCE_SETTLEMENT / REAL_ACCEPTED_SOURCE_V4_15 labels. Original R20 receipts, gates, seal, runtime and accepted business algorithms remain unchanged. The replacement capabilities are:

| Capability | Status |
|---|---|
| V4_15_RUNTIME_ENGINEERING | PASS |
| REAL_ACCEPTED_SOURCE_T0_INTEGRATION | PASS_CAPABILITY_SCOPED |
| REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK | PASS_CAPABILITY_SCOPED |
| REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT | NOT_GRANTED_PENDING_MATURITY_EVIDENCE |
| HISTORICAL_PIT_EFFECTIVENESS | NOT_GRANTED |

Cross-cutting audit item `R20_AUDIT_P0_REAL_MATURED_SCOPE` is tracked independently in OPEN_VALIDATION_DEBT.json, with exact feasibility evidence and separate acceptance. Scope-label repair is PASS_LOCAL; actual real-maturity evidence debt remains OPEN. It does not block unrelated engineering after appropriate external stage authorization, and does block claims that specifically need matured real settlement. It grants no promotion or next-stage permission.

Accepted-session ingestion can invoke `python -m scripts.r20r1_maturity_debt <exact_packet_list.json>` to accumulate append-only proof receipts. The independent packet validator requires an exact sealed real owner publication, REALTIME_ACCEPTED enrollment, T0 freeze before endpoint opening, accepted Data Head-authorized complete future endpoints, and independently verified numerical outcomes at the frozen horizons/evaluation basis. A verified real maturity receipt closes only its explicitly evidenced scope; other horizons stay restricted, and PIT never auto-upgrades. With no packets, the current persisted debt revision remains OPEN, idempotently. No maturity waiting or scheduled future run is needed for this task.

The independent scope oracle does not import the writer, scope-admission function, or Radar/Settlement evaluators. Adversarial tests reject all-PENDING / zero real future reads, engineering/synthetic/vector/historical-prices-only inputs, reconstructed-as-of upgrades, raw fallback, future read before freeze, unbound scope widening, premature debt closure and Stage/Data/operational permission changes.

Validation: 51 focused scope/debt tests; clean detached validation runs all 107 existing R20 current tests plus these new tests. Historical 1168 + R19 62 retain their prior externally audited source contexts without needless rerun. Exact counts, source identity and clean checkout status are in R20R1_TESTS.json and clean_regression/CLEAN_DETACHED_REGRESSION.json. The final candidate seal binds the tested implementation's immutable Git tag and final-branch ancestry; final seal delta is evidence only.

Protected final state: no V4-15 Accepted Head; Stage V4_00_TO_V4_14_ACCEPTED; Data 2026-09-30; Production/Shadow/Focus/V4-16 false. NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT.
