# V4 R16 — Operational Daily Source/PIT and Incremental Executor R1

## Code path

`operational_daily_executor_v1.execute_sources` validates the requested session against the post-close gate, freezes official TDX package bytes, extracts only the requested T0 bars, verifies the BaoStock runtime acceptance and preserved native responses, normalizes daily/factor responses, applies the existing local fallback/reconciliation rules, and seals a local source freeze. `verify_source_gate` checks dated provider facts and the prior accepted identity scope. When ready, `derive_ready_sources` reopens the immutable freeze at the final boundary, rechecks the gate, runs `operational_daily_ready_owner_v2.build`, creates the Core candidate, runs existing owner/sector producers and read-index projections, then prepares a successor candidate. Existing publication CAS/readback is only reached when an explicit local readback endpoint is supplied.

## Incremental observability added

`V4_DAILY_PIPELINE_PROGRESS_R1` wraps the existing executor progress callback without changing its call contract. It records first checkpoint time, elapsed time since that stage's first checkpoint, interval since the prior checkpoint, previous checkpoint name, and nonnegative row/security/processed/cache counters. The timing scope is explicitly `CHECKPOINT_INTERVAL_NOT_ISOLATED_STAGE_BENCHMARK`; it does not claim per-stage CPU time or end-to-end performance. Rewrapping is idempotent. Executor failures keep their existing status/checkpoint boundary; frozen source/readiness files remain the existing recovery checkpoints.

## PIT, source, and write status

- The active source executor currently emits `AS_RECORDED=False` and `PIT_ELIGIBLE=False`; local provider verification is historical/offline diagnostic evidence, not proof the values were available at the original T0 decision time.
- The authority registry has no approved independent receipt issuer; no production key/authority or calendar was created. A future onboarding must independently verify issuer ownership, key custody/public-key distribution, Shanghai session calendar, exact receipt fields, and revocation/rotation before enabling R3 acceptance.
- The frozen source artifact currently does not provide the separately accepted `security_universe` fact needed by R14. No source/Universe/full-market/publishable PASS is claimed.
- Local offline execution candidates can be inspected; this stage did not execute a PG writer, persist source packages, update accepted Head, schedule automation, or start 28765/28766.

## Acceptance

`CODE=PASS_PROGRESS_INSTRUMENTATION`; `SOURCE_REAL=BLOCKED_NO_APPROVED_T0_RECEIPT_AND_NO_ACCEPTED_UNIVERSE`; `PIT_REAL=BLOCKED_AS_RECORDED_FALSE`; `PG_LIVE=NOT_RUN_NO_READER_OR_WRITER_DSN`; `HEAD=NOT_CHANGED`; `PRODUCTION=UNCHANGED`. Checkpoint duration data is not a real-day performance benchmark.

Focused executor tests and counts are recorded in the R16 stage report.
