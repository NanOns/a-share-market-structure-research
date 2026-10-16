---
stage_id: V4_PG_DAILY_PUBLICATION_R5_20261016
code_sha: f0e4ef7da7e55a9b302c928ca0ba9625c57228ef-base-plus-R5-worktree
test_scope: manifest-package-authority-date-validation-business-release-boundary-page-readback
conclusion: 51-focused-tests-pass; daily-chain-suite-7-pass-1-preexisting-fixture-failure; real-producer-pg-and-business-publishability-blocked
approval_status: CODE_ONLY_REPAIR_AUTHORIZED
---

# V4 PG 日发布 R5 阶段报告

- Stage: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R5`
- Frozen audit baseline: `f0e4ef7da7e55a9b302c928ca0ba9625c57228ef`
- Branch: `codex/v4-workspace-cleanup`
- Upgrade documents consulted: R4 design/report, R8 unified-source repair contract, actual current V4 daily executor and operational runtime contracts.
- Scope: readiness separation, accepted package authority, strict dates, revision-aware event and lifecycle page reads.

## Implemented

- `METADATA_CANDIDATE_READY` is an explicit metadata-only status. The candidate reports `BLOCKED_BUSINESS_PUBLISHABILITY` and `BLOCKED_CORE_RESULT_NOT_BOUND`; the pure Head planner rejects it. Existing optional Owner families remain optional and cannot stand in for core daily business data.
- Source manifest R2 hashes PG package-authority fields together with each consumed source revision. New PG migrations bind inserted revisions to an immutable `ACCEPTED_SOURCE_PACKAGE` and require manifest R2 on new publications. Existing unbound revisions are not backfilled.
- Candidate and reader reject noncanonical/impossible dates, invalid effective windows, package/publication T0 mismatch, prior-day package observation, unaccepted/unbound packages, tombstones, digest mismatches, and the existing schema-defined clock failures.
- Summary event selection is scoped to exact publication ID and revision and chooses only the newest observation per logical event before applying ACTIVE/RETRACTED. Current-page projections expose exact present fields, missing fields, and `PG_FIELD_VERIFIED` / `PROJECTION_READY` / `SOURCE_MISSING` / `CONTRACT_UNKNOWN` status.
- The actual daily executor was traced through source capture, deriving, sealing, and file Head CAS/readback. It does not persist its accepted source package, source revisions, consumed-source manifest, or daily core result into the R5 PG publication relations. The boundary therefore remains blocked.

## Tests

- **Passed 51:**
  `python -m pytest -q -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/v4_daily_publication_r5 tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py tests/test_v4_pg_publication_contract_static.py tests/test_v4_pg_source_manifest.py`
- **Passed 2:** `tests/test_operational_daily_executor_v1.py` with its own G-drive basetemp.
- **Daily-chain spot check: 7 passed, 1 failed.** The failure is `tests/test_pre_next_t0_executor_chain.py::test_full_executor_entry[True]`, which stops before the modified code path because its temporary checkout lacks `config/operational_daily_exact_release_policy_v2.json`. This is recorded as a fixture/environment failure, not a passing regression.
- No production PG connection, migration, data write, Head change, service start, or 28765 deployment was performed.
- GitHub Actions/CI: pending push.

## Status and blockers

- Code: `R5_CODE_PARTIAL_PASS`.
- PG live: `PG_LIVE_NOT_VERIFIABLE` (no approved read-only DSN configured).
- Business publication: `BUSINESS_PUBLISHABLE_BLOCKED` (no current canonical PG producer or publication-bound daily core result relation).
- Production data, accepted Head, and 28765: unchanged.

## Next action

Implement and independently audit the real daily-executor adapter that persists accepted package/revision provenance and consumed sources into PG, then bind actual core daily business results. Update this report and Issue #2 / PR #3 with final commit SHA and CI evidence after push.
