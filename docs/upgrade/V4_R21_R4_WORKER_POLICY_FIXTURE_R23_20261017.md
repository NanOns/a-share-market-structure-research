stage_id: V4_R21_R4_WORKER_POLICY_FIXTURE_R23_20261017
baseline_sha: 50b8b1b57a7060583784c184e369a53b76197541
branch: codex/v4-workspace-cleanup
status: CURRENT_WORKER_REGRESSION_FIXTURE_ALIGNED
callsite_ids: none; test fixture maintenance only
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue operational Head/Owner PG migration and remaining exact business consumers
---

# V4 R21-R4 worker exact-policy fixture repair

Date: 2026-10-17 (Asia/Shanghai). This is adjacent CI maintenance discovered by the R22 focused regression selection.

## Change and verification

- Updated the frozen-worker activation test fixture to provide an isolated exact daily policy file, its SHA-256 in the mocked package resource manifest, and an explicit verified policy binding.
- The test continues to assert that a producer worker verifies its package without acquiring the desktop workspace lease.
- The combined focused Owner manifest, Reader fallback, BFF descriptor, shadow cache and runtime source mode selection passed: **17 passed**. `compileall` and `git diff --check` passed.

## Accounting and limits

- This changes no baseline consumer and closes no P1 row: **0/266 formally complete, 266 remaining**.
- PostgreSQL and live business acceptance were not exercised. The fixture verifies only the worker admission invariant covered by this test.

## Next stage

Continue the actual PG-backed operational Head/Owner migration and remaining mapped business readers. Retain the live PG and per-callsite acceptance gates.
