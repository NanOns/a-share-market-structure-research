# V4 PG 日发布 R5 真实发布边界修复

- Contract: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R5`
- Frozen audit baseline: `f0e4ef7da7e55a9b302c928ca0ba9625c57228ef`
- Branch / PR / Issue: `codex/v4-workspace-cleanup` / #3 / #2
- Upgrade basis: R4 publication repair and report; `V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`; current operational daily executor and runtime contracts.
- Scope: distinguish metadata candidate from business release; bind new PG source revisions to immutable accepted packages; harden date and source checks; report exact current page field coverage.
- Boundary: code and tests only. No migration execution, production PG DML/DDL, Head switch, service start, 28765 deployment, Git history rewrite, or physical deletion.

## Metadata candidate and business publication

Candidate `status=METADATA_CANDIDATE_READY` now means only that the supplied identity, source manifest, optional Owner contracts, and their metadata checks pass. The candidate reports `publish_status=BLOCKED_BUSINESS_PUBLISHABILITY` and `business_publishability_status=BLOCKED_CORE_RESULT_NOT_BOUND`. The Head planner rejects this state. Optional `research_priority`, `operational_risk`, and `sector_lifecycle` rows remain optional capabilities; they are not reclassified as daily core results.

The minimum daily contract is now `V4_DAILY_PUBLICATION_MINIMUM_R2`. Its release boundary explicitly requires a bound core business result. No current V4 daily producer writes a verified business result into the PG publication contract, so there is no path to `PUBLISHABLE_BUSINESS_SNAPSHOT` in this code. This is an intentional business-release block rather than a metadata failure.

## Actual producer and source authority

The actual path traced in code is `core_product_server_r1` / `operational_daily_server_v1` → `DailyJobs` → `operational_daily_executor_v1.execute_sources` → immutable `DYNAMIC_DAILY_SOURCE_FREEZE_V1` (TDX target bars, accepted Baostock responses, runtime receipt) → `derive_ready_sources` / sealed daily candidate → `operational_successor_release_v1.promote` (file Head CAS and HTTP readback). It does not write `v4.source_packages`, `v4.source_revisions`, `v4.publication_consumed_sources`, or PG business result relations.

Migrations `034_source_package_revision_authority_r2.sql` and `035_source_manifest_contract_r2.sql` add the minimum database-side contract for a future producer: every new canonical source revision insert must name a source package; the FK must resolve to an `ACCEPTED_SOURCE_PACKAGE`; package authority is immutable; new publication rows must use manifest contract R2. Existing source revisions remain unbound and are not silently backfilled or promoted. These migrations are **not applied**.

Manifest contract `V4_PG_CONSUMED_SOURCE_MANIFEST_R2/2.0.0` hashes the joined persisted revision and package authority fields. The reader joins package rows from PG for the selected publication's exact consumed sources and independently checks digest equality, accepted scope, package date, same-day package observation, T0 window, tombstone, and availability clocks before rehashing. The pure candidate planner still receives caller-supplied rows; it explicitly does not attest their PG origin and cannot pass business publishability.

## Dates and current page reads

Date strings require canonical `YYYY-MM-DD`, valid calendar dates and ordered effective windows. The package target trade date must equal publication T0. A package observation earlier than T0 (in `Asia/Shanghai`) is rejected. Existing source rules retain the schema-defined `system_available_at >= observed_at, ingested_at` relation and acceptance-time limits; no unsupported provider-clock ordering rule was added.

Summary event reads now select the highest observation revision for each logical event within the exact publication ID **and publication revision**, then include only its ACTIVE state. This avoids showing an older ACTIVE event after a later retraction. Event payload trade dates must match T0. Entity lifecycle rows remain bound to consumed source revisions and T0-effective windows; missing identity/quality is rejected. Page responses expose exact field mappings and the states `PG_FIELD_VERIFIED`, `PROJECTION_READY`, `SOURCE_MISSING`, and `CONTRACT_UNKNOWN`. OHLCV, replay, names, publication-bound membership, cohort and settlement remain unavailable where the schema has no verified relation.

## Acceptance record

- Code status: `R5_CODE_PARTIAL_PASS` — deterministic validation and release-boundary fixes pass; actual producer-to-PG persistence and publishable core result are still missing.
- Live PG: `PG_LIVE_NOT_VERIFIABLE`; no approved read DSN was available. Migrations, catalog, source rows, and Head were not queried or changed.
- Business release: `BUSINESS_PUBLISHABLE_BLOCKED`; no canonical daily PG writer or publication-bound daily price/core result exists in the traced execution chain.
- Production, accepted Head, 28765, and stored business data: unchanged.
- Tests and CI: recorded in `reports/stage/V4_PG_DAILY_PUBLICATION_COMPREHENSIVE_TEST_REPORT_20261016_R5.md` and GitHub Issue #2 / PR #3 after push.

## Next work

Implement and independently audit the first real adapter from the existing daily executor into the PG source-package/revision and publication-consumed-source relations, followed by a binding for actual core daily business results. Validate only with an explicitly approved read-only PG identity and an isolated writable PG environment when transaction tests are authorized. Keep production DML, Head transition, and deployment as separate approvals.
