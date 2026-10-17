---
stage_id: V4_R21_PG_ONLY_CONSUMER_MIGRATION_20261017_R1
baseline_sha: 81f7398d52a786a0c0d4570a988f6aeeabf9b3f5
code_sha: fe0907891b81813a6f8ffa9e19ceb5306db49f9a
branch: codex/v4-workspace-cleanup
scope: explicit TDX source-root boundary for official and latest package capture
test_scope: TDX source-root boundary regressions and focused V4 PG candidate CI suite
conclusion: R21_CODE_PARTIAL_OWNER_AND_BUSINESS_READ_MIGRATION_OPEN
P1_business_reads_before: 266
P1_business_reads_after: 266
approval_status: source-code-and-test-changes-authorized; PG DDL DML Head switch and production deployment not authorized
---

# V4 R21 PG-only consumer migration progress R1

Date: 2026-10-17 (Asia/Shanghai). The active stage input is Drive task card `V4_R20独立外审_R21_PGonly业务文件读取迁移与源输入边界任务_R1_20261017.md`. The applicable upgrade documents were `docs/upgrade/V4_R18_INCREMENTAL_PERFORMANCE_RECOVERY_MATRIX_R1_20261016.md` and `docs/upgrade/V4_R20_BUSINESS_CODE_FILE_ACCESS_AUDIT_R1_20261017.md`. The accepted R19/R20 scans were used as the baseline; they were not repeated.

## Completed code batch: TDX path boundary

- `capture_tdx_official_daily_package`, `capture_latest_tdx_package`, and `extract_target_session_bars` no longer default to `D:/new_tdx`. An omitted root resolves through `common.paths.resolve_tdx_root`, which accepts the configured `config/paths.yaml` root or `TDX_ROOT` and fails closed when neither exists; tests pass an explicit isolated test root.
- The current challenge-downloader adapter now reads the exact receipt reference returned by its bounded subprocess and verifies that receipt and package. It no longer consumes its `reports/audits` pointer file.
- This change only tightens the source-root safety boundary. It does not establish source issuer/PIT acceptance or a PG ingestion/readback path, and it does not represent any of the 266 business-file P1 call sites as migrated.
- Targeted local regression result: 62 passed. The final push and PR CI on `fe0907891b81813a6f8ffa9e19ceb5306db49f9a` both passed admission and V4 candidate jobs; the focused CI suite reported 232 passed and 1 skipped. `git diff --check` and staged repository policy passed. No PG connection, server, market source request, Head, scheduler or production operation was performed.

## Remaining R21 gates

| Work package | Current disposition | Evidence needed to close |
|---|---|---|
| 200 Owner reads / 52 source files | OPEN; 0 migrated in this batch | Per-callsite Owner contract and relation mapping; same-T0, source digest, namespace, publication/revision and completeness proof; typed PG Reader and paired integrity tests |
| 28 other business reads / 21 files | OPEN; 0 migrated in this batch | Exact publication-bound relation and consumer field mapping; explicit DEGRADED/BLOCKED behavior; no file fallback |
| 38 external market-data reads / 11 files | OPEN; 0 migrated in this batch | Distinguish ingress from consumers; source manifest, first-available timestamp, original SHA, calendar and authorized PG-ingestion plan |
| 331 dynamic write destinations | OPEN; not classified in this batch | Call-chain and output-purpose evidence for business state, process state, logs and temporary output |
| 52 configuration reads | OPEN; not classified in this batch | Per-input identity and invariant/environment role; `config/` path alone is insufficient |
| 58 stale policy identities | OPEN; not re-audited | Confirmed runtime loader-chain evidence; preserve accepted Head and identity |

Existing publication readers cover only documented Owner families and accepted Publication rows. The R20 business inventory identifies callsites and source hashes but does not include stable `reference_id` fields; the linked full evidence must supply the source-row identity before a complete 266-row migration matrix can claim origin reference IDs. No fabricated IDs or P1 severity downgrades are used here.

## Acceptance boundary and next work

This is a code partial result, not `CODE_PASS` for R21 and not V4 production readiness. The P1 counter remains 266. No compliant live PG Reader identity was supplied, so live PG readback is unverified; no new schema was executed. Next: produce the source-evidence-backed callsite matrix, then migrate active Owner consumers onto existing publication/Owner typed readers in dependency batches and prepare only necessary DDL/role/rollback drafts. Any isolated or production PG DDL/DML, accepted Head change, or 28765 deployment remains separately gated.
