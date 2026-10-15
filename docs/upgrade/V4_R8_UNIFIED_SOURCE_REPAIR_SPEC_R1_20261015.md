# V4 R8 unified source repair — S3 design contract

- Contract: `V4-R8-UNIFIED-SOURCE-REPAIR-20261015/R1`, P0-D/P0-E/P0-F.
- Consulted sources: the R8 task card sections 2 and 5; `docs/upgrade/V4_R7_FORWARD_SIGNAL_SPEC_R1.md`; the R6 immutable operational risk PG owner and BFF read path.
- Base: fixed branch `codex/v4-unified-development`, R6 `e44a55609168344b820138efc01d53d76b7312df` plus pushed S1/S2; S2 commit `986de69d3eafdf58e6bc292382f4ad558cc70889`.

## P0-D — observation and publication identities

New observations use `V4_FORWARD_OBSERVATION_ID_R2`, binding T0, evidence Lane, rule and version, entity, capture revision, and source digest. New daily universe, schedule, aggregate, and publish pointer keys include Lane and revision/digest. Same T0 can publish Lane H, Lane L, and late observations independently. Equal revision with different content fails closed; changed content needs a higher revision. Existing unversioned R7 facts remain immutable and are read as Lane H only. Default reads select the latest capture revision within each T0/Lane/rule/entity; explicit revision reads remain available. Settlement schedules append by `(observation_id, horizon, settlement_revision)` and readers choose the latest settlement revision for that observation only.

## P0-E — accepted-session advancement

After successful Head CAS/readback, the Forward post-publication observer queries only accepted due sessions whose latest schedule remains pending or unresolved, loads each bound raw/lifecycle source, and appends a settlement revision using those accepted prices. It never revises the frozen T0 observation. The nominal unadjusted close basis and lack of corporate-action adjustment remain explicit. Successful runs and retryable failures are append-only PG facts. A later accepted Head rechecks unresolved schedules, allowing an actual due result to be appended without backdating the original observation.

## P0-F — risk producer and consumer

`operational_risk_v1.py` remains the only transition producer under `V4_OPERATIONAL_RISK_CHANGE_R2`; the R6 content-addressed PG owner accepts R1 history and R2 writes. The home and risk detail consumers continue to load the immutable R6 PG owner and expose its binding/token. S3 targeted vectors cover direction and first-observed denominators; isolated PG consumer readback remains part of S4.

## Stage acceptance boundary

Targeted tests and in-memory/mock store checks establish source semantics only. S3 does not claim real PG coexistence/readback. S4 must demonstrate immutable legacy facts, same-date dual-Lane coexistence, revision/idempotency behavior, due-settlement append and retry, R6 risk consumer binding, and query consistency using a disposable isolated PostgreSQL cluster under `G:/codex_tmp/test_temp`.

## S4 evidence and change note — 2026-10-15

S4 validation exercised Forward and the R6 risk PG Owner against one disposable PostgreSQL cluster under `G:/codex_tmp/test_temp`, with source documents read from the accepted source root. The isolation contract and measured query plans are recorded in `reports/audits/v4_unified_r8/CRITICAL_BUG_REPAIR_EVIDENCE.json` and `R6_R7_SOURCE_DIFF_AND_MERGE_MATRIX.md`. Date-scoped observation and schedule reads now use fact-key range predicates so the existing `(kind, fact_key)` primary key can bound reads. Compact R7 aggregate facts feed the counts, audit-date, and matured-count readers. No business facts or files in the source root were modified.

S4 acceptance is scoped to isolated PG coexistence/readback, source semantics, and bounded query plans. True LIVE_OOS and the 10/14 due settlement still await a future accepted Head; the isolated Lane L sample is only an engineering fixture. S5 records the task-card I-01–I-10 disposition and next production build entry without running a build.

## S5 final closeout note — 2026-10-15

The task-card I-01–I-10 dispositions and `UNIFIED_SOURCE_ACCEPTANCE_PASS` are recorded in `reports/audits/v4_unified_r8/R8_UNIFIED_SOURCE_FINAL.md`. Real future LIVE_OOS and unaccepted 10/14 settlement remain explicit future-session dependencies. The next build entry is one candidate at the final fixed-branch SHA, isolated package proof, then one planned production window; no package or deployment was run during R8.

## R8 isolated lifecycle driver admission R1 — actual two-session catch-up

The actual post-close 10/14–10/15 source batch passed both source gates. Its
first candidate computation stopped at the accepted market driver's whole-file
revision check: R8 adds target lifecycle identity arguments to the Owner IO
adapter. This gate remains unchanged for production execution.

`R8_ISOLATED_LIFECYCLE_DRIVER_ADMISSION_R1` permits candidate computation only
when `candidate_only_exact=True` and the root resolves below `G:/codex_tmp`.
An AST comparison against the hash-verified accepted adapter recognizes exactly
the lifecycle contract declaration, optional lifecycle argument, four identity
read statements and three identity keywords to `materialize_core`. After those
exact additions are removed, the entire module AST must equal the accepted
module. Any other market or numeric change still requires range repair. The
revision receipt records both source bindings, keeps `unchanged=False`, and
explicitly sets `production_admitted=False`; actual daily numeric QA is still
required. This is not production policy admission or release acceptance.

The actual accepted pre-R8 adapter is retained as the portable audit fixture
`tests/fixtures/r8_owner_adapter_before.txt`. Targeted guard tests include changed
market dispatch, changed identity arguments, an unrelated extra statement,
production-path rejection, and numerical-kernel rejection. These plus the
existing revision tests passed (18); existing R8 member/settlement tests passed
(19). Real two-day computation and final per-day QA are recorded separately in
`TWO_SESSION_20261014_15_CATCHUP.json`.
