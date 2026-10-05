# FEP E1R1 blocker repair completion

Baseline: `e4ea913d8926e904e55cbf16993ec63c0e90b031`.
Task: `V4_15E1_R1_BLOCKER_REPAIR_TASK_20261005.md`.

Local exit: **BLOCKED**. Next: **STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION**.
This delivery does not grant external acceptance or E2 entry.

WP-A closed: formal external design receipt copied exactly, 14019 bytes and SHA256
`cd279e26fb9753eb1e333c7554f9f06393c9232ee44ff7be6d86e2f2f65d178e`.
Original candidate seal retained and receipt bindings updated.

WP-B remains blocked. Historical V4-03 paths exist for all 47 fields. Explicit
current sealed Core owner inventory covers 5224 rows and proves 40 reconstructed
value/quality/digest/window/available_at paths. Missing current fields:
rel_market_1, rel_market_3, rel_market_5, rps20, rps20_delta3, rps5, rps5_delta1.
V4-12 explicitly marks rel_market_1 UNKNOWN because the exact target-date V4-03
factor publication is not bound. Reconstructed engineering owner inputs cannot
manufacture current FIRST_OBSERVED ENTRY identity. No aliases, latest/mtime
availability, reduced field contract, or incomplete real snapshot was admitted.
Discovery samples of other owners are identified as samples, not full-market
proof. Full inventory proof covers the exact current Core owner artifact.

WP-C closed for engineering: versioned additive V4-15 label-time authority and
adapter use exact allocated row/receipt identities. Source time consumes every
registered fact, maturity requires full window and quality, revision visibility
is independently enforced. T3 and T5 reject; T6 admits the isolated fixture.
The five current real pending rows have NOT_PROVEN times and no training binding.
CURRENT_REAL_MATURITY_EVIDENCE=NONE; PROVED_HORIZONS=[]. No label recomputation.

WP-D namespace inventory closed: immutable V1 retained, V1.1 explicitly adds all
33 FEP declarations as REFERENCE engineering namespace, no migration/cutover
grant. The original inventory test reads the successor and passes undeselected.

A newly exposed cross-stage conflict remains: R25 protects all historical tracked
bytes, including the exact V4-18 test that this task authorizes changing. Its
preflight source is itself exact-bound; an in-place guard patch was not retained.
Independent audit item FEP_E1_R1_R25_HISTORICAL_GUARD_CONTRACT_CONFLICT records the
exact cause and requires versioned owner reconciliation. No old V4-16 dependency
or accepted head was rewritten to hide this failure.

Validation: fresh PostgreSQL 78 passed / 1 skipped;
upgrade 79 passed / 0 skipped. 33 tables,
32 immutable guards, role/search_path/CAS concurrency/rollback and existing
40 negative-vector semantics remain verified; migrations 028–031 unchanged.
Repair unit/static gate: 41 passed.
Scoped regression: 2389 passed, 3 skipped,
55 full-run failures. A focused governance
retest closes the sample-identity-in-config failure after moving sample records
to evidence. Active failures: 54, including
52 existing debts. Full-run counts are retained without fabricating a full rerun.
Introduced active nodes: ['tests.test_r25_packet::test_actual_authority_inventory_waits_without_target', 'tests.v4_dm01_r4r2.test_acceptance_seal::test_sealed_future_wait_has_no_source_or_publication'].
Only the previously governed superseded R4 node remains deselected.

All protected accepted heads retain exact bytes. Production/Shadow/Focus=false;
MODEL_DISPLAY/PRIORITY_USE/FEP_PRODUCTION=UNGRANTED. E1/V4-16 accepted heads absent.
The two new PostgreSQL instances are isolated on E:, stopped after evidence capture;
data and raw logs retained. Main fresh/upgrade FEP tables remain empty. TDX untouched.

Evidence: LOCAL_ACCEPTANCE_MATRIX.json, SCOPED_REGRESSION_SUMMARY.json,
PASS_KEEP_DATABASE_READBACK.json, FEATURE_MAPPING_CONTRACT_CONFLICT.json,
R25_HISTORICAL_GUARD_CONTRACT_CONFLICT.json and candidate seal in this directory.
