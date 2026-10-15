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
