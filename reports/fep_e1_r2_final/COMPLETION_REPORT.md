# FEP E1 R2 final reconciliation

Baseline: `7474fb25c93286b0224635b77033451a81955ae1`.
Authority: `V4_15E1_R2_FINAL_OWNER_AND_GOVERNANCE_REPAIR_TASK_20261005.md`.

**PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT**.
Next: **STOP_WAIT_FINAL_E1_EXTERNAL_AUDIT**. E2 remains unauthorized.

Path A uses the exact accepted historical V4-03 full-scope owner dated
2026-09-24. Its 5222 rows contain all 47 accepted field envelopes. The adapter
copies values, quality, source/input digests and window identities without
factor formulas or aliases. All seven relative/RPS fields are present in the
accepted historical owner. UNKNOWN remains an explicit envelope, never imputed.
The existing incomplete 2026-09-30 owner is not rewritten or promoted.

One reproducible engineering observation/snapshot consumes the 47-field adapter.
Its exact dependency manifest binds the owner head/artifact, source row digest,
algorithm/parameter/feature contracts, calendar, universe and adjustment source
identities. Binary upstream inputs are exact-hash checked and bound through
readback receipts. RECONSTRUCTED_ASOF/REPLAY only; AS_RECORDED/FIRST_OBSERVED=false.
The local capture receipt proves present engineering readability; it does not
substitute wall-clock time for historical first availability. The engineering
slot ceiling is a read boundary; prediction/model deadlines remain disabled.
Repeated reads of the same capture give the same feature digest.

The original V4-18 test was restored to git blob
`26369110c8ea35b9c1d216df17d11f981047fcef`. V1 and V1.1 contract bytes remain
unchanged. A new additive successor test covers all current SQL declarations,
including 33 explicit FEP REFERENCE engineering declarations. V4-18 execution,
production cutover and accepted head remain ungranted/absent.
The exact obsolete V1 inventory node is registered SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION,
and is not counted as PASS. No R25 preflight or dependency bytes were patched.
protected() passes and selection() returns WAIT_ACCEPTED_DAILY_INPUT.

Minimal real PostgreSQL replay/readback retains unchanged 028–031 migrations,
33 tables, 32 guards, role/search_path, CAS/rollback/idempotency and equal
fresh/upgrade schema identities. No database rebuild was performed.
Fresh targeted: 94 passed / 1 skipped / 0 failures.
Upgrade targeted: 95 passed / 0 skipped / 0 failures.
Full final scoped regression after all changes: 2485 passed,
4 skipped, 52 existing failures,
0 introduced active failures. Existing debt: 43 registered + 9 independently
reproduced baseline nodes. The only two deselections are the governed pre-seal
R4 assertion and the newly governed pre-FEP V1 inventory assertion.
Raw logs/XML and exact candidate bindings are retained.

Current real labels remain pending, CURRENT_REAL_MATURITY_EVIDENCE=NONE,
PROVED_HORIZONS=[]. The three-time authority and raw external design receipt
remain exact PASS_KEEP. No label recomputation, real training binding, model
training, production/Shadow/Focus or model display/priority grant occurred.
Accepted Stage/Data/owner heads are unchanged; FEP E1/V4-16 heads were not created.
TDX is read-only and untouched. Isolated E: PostgreSQL instances are stopped,
with data and raw logs retained. Unrelated untracked work is preserved.
