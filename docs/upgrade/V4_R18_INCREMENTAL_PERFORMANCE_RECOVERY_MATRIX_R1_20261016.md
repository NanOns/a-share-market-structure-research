# V4 R18 — Incremental Performance and Recovery Matrix R1

## Scope and environment

This matrix covers the current V4 publication, source, Core, Owner, API and Universe paths on the R14–R18 branch. It excludes pre-V4 V1/V2/V3 suites and M14. Local fixed-service listeners 28765/28766 and a least-privilege PG reader/writer were unavailable; no PG/server/browser writes or real daily run occurred. R18 therefore reports code/test readiness separately from isolated-PG, real-daily, and production readiness.

## Scenario matrix

| Scenario | Current V4 evidence path | Test class / outcome boundary | Remaining live evidence |
|---|---|---|---|
| New T0 only | `execute_sources` target extraction and source readiness | synthetic/frozen bytes; checkpoint instrumentation | accepted real source receipt, PIT clock, independent Universe, actual incremental row counts |
| Previous-day correction | source revision and `v4_history_corrections_pg_v2` exact append scopes | focused correction contract tests | approved PG transaction/readback and real correction dataset |
| Adjustment/factor source revision | BaoStock normalize/factor contract and readiness binding | executor/source ingest fixture tests | real T0 raw response and measured partial recompute |
| Halt/no-bar, new listing, delisting, code migration | market Universe completeness and native source reconciliation | explicit fixtures, including lifecycle and scope rules | accepted independent dated identity and real T0 source facts |
| Temporarily absent source / retry | `WAIT_TDX`, source readiness, immutable freeze/readiness checkpoint | executor and pre-next chain tests | a real trading-session retry and durable evidence |
| PG restart / timeout | caller-transaction boundary, read-only reader and candidate error handling | unit/fake connection and schema-contract tests only | authorized isolated PG restart, rollback, replay and independent readback |
| Duplicate execution | immutable freeze/revision identity and existing candidate idempotency | focused fixture regression | real same-day replay against PG ledger and publication state |
| Two concurrent T0s | publication identity and candidate planning constraints | static/unit contract coverage only | authorized concurrent PG exercise |
| Same-T0 revision race / Head CAS | existing `plan_publication_head_change` CAS contract; no Head is changed here | unit candidate tests | authorized accepted Head CAS race exercise |
| Seven API page reads | same candidate token/T0/namespace; per-field coverage in adapter | BFF contracts/unit tests only | real accepted Publication and browser traces at two viewports |

## Measurement contract

`V4_DAILY_PIPELINE_PROGRESS_R1` records timestamps only at existing executor checkpoints: stage first-seen elapsed, interval to preceding checkpoint, checkpoint name, and available row/security/processed/cache counters. No current instrumentation isolates all source/CPU/SQL/page phases, samples peak memory, captures EXPLAIN plans, or times a real PG read/write. No real-day performance number or speedup claim is made. The next approved measurement should retain the exact source/package/Universe and publication identity and separately time TDX reads, BaoStock network/normalize, K/MA/Profile, membership/sector, each Owner, Universe, PG commit/readback, candidate/CAS planning, and each BFF route; capture row counts, cache hits, peak memory, and query plans.

## Readiness conclusions

- `CODE_READY`: `PARTIAL` — Core/Universe gates, migration draft, reader/writer contracts, existing retry/replay boundaries, API contracts, and checkpoint instrumentation are implemented and covered by focused V4 tests.
- `ISOLATED_PG_READY`: `BLOCKED_NOT_AUTHORIZED_AND_NO_ISOLATED_TARGET` — no migration or isolated PG write was run.
- `REAL_DAILY_READY`: `BLOCKED_NO_APPROVED_ISSUER_CALENDAR_UNIVERSE_AND_PG_ROLES` — actual data/source authority and PG identities are absent.
- `PRODUCTION_READY`: `BLOCKED` — no live PG publication/readback, seven-page browser evidence, measured real performance, accepted Head, or 28765 deployment authorization.

## Project original 22 phases

The current repo and task card do not contain the formal source that enumerates the product's original 22 phase names and acceptance criteria. Accordingly the stage report lists entries 01–22 as `UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE`; R14–R18 execution batch names do not substitute for them.
