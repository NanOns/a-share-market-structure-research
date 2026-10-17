---
stage_id: V4_R21_PG_ONLY_CONSUMER_MIGRATION_20261017_R1
baseline_sha: 81f7398d52a786a0c0d4570a988f6aeeabf9b3f5
code_sha: cc9ec42be
branch: codex/v4-workspace-cleanup
scope: TDX source-root boundary; PG-only Owner and active page reads; 266-callsite reference crosswalk
test_scope: TDX regressions, focused PG-only reader regressions, and required push/PR candidate CI
conclusion: R21_CODE_PARTIAL_OWNER_AND_BUSINESS_READ_MIGRATION_OPEN
P1_business_reads_before: 266
P1_business_reads_after_formal_inventory_reconciliation: NOT_RUN
P1_code_paths_with_implementation_pending_reconciliation: 21
P1_ingress_adapters_still_open: 8
approval_status: source-code-and-test-changes-authorized; PG DDL DML Head switch and production deployment not authorized
---

# V4 R21 PG-only consumer migration progress R1

Date: 2026-10-17 (Asia/Shanghai). The active stage input is Drive task card `V4_R20独立外审_R21_PGonly业务文件读取迁移与源输入边界任务_R1_20261017.md`. The applicable upgrade documents were `docs/upgrade/V4_R18_INCREMENTAL_PERFORMANCE_RECOVERY_MATRIX_R1_20261016.md` and `docs/upgrade/V4_R20_BUSINESS_CODE_FILE_ACCESS_AUDIT_R1_20261017.md`. The accepted R19/R20 scans were used as the baseline; they were not repeated.

## Completed code batch: TDX path boundary

- `capture_tdx_official_daily_package`, `capture_latest_tdx_package`, and `extract_target_session_bars` no longer default to `D:/new_tdx`. An omitted root resolves through `common.paths.resolve_tdx_root`, which accepts the configured `config/paths.yaml` root or `TDX_ROOT` and fails closed when neither exists; tests pass an explicit isolated test root.
- The current challenge-downloader adapter now reads the exact receipt reference returned by its bounded subprocess and verifies that receipt and package. It no longer consumes its `reports/audits` pointer file.
- This change only tightens the source-root safety boundary. It does not establish source issuer/PIT acceptance or a PG ingestion/readback path, and it does not represent any of the 266 business-file P1 call sites as migrated.
- Targeted local regression result: 62 passed. The final push and PR CI on `fe0907891b81813a6f8ffa9e19ceb5306db49f9a` both passed admission and V4 candidate jobs; the focused CI suite reported 232 passed and 1 skipped. `git diff --check` and staged repository policy passed. No PG connection, server, market source request, Head, scheduler or production operation was performed.

## Completed code batch: PG-only Owner and page read paths

- `v4_operational_owner_pg_closeout.read` and cached attestation now validate an inline, digest-bound PostgreSQL descriptor and read the append-only PG fact in a read-only transaction. They compare the original source binding stored in the PG payload without reopening the source file. Publication still verifies source bytes before writing the fact.
- `v4_membership_reference_pg_v1` now stores its membership/identity reference authority as a `forward_facts` PG fact. Membership, identity, search-identity, and research readers load that authority and payloads through PG; missing or legacy file-only authority fails closed. Original source artifacts remain publisher inputs where the code copies them into PG.
- Active `CoreProductBFFR1` paths no longer read identity files, display-name files, legacy gzip Focus projections, or legacy file market-fact payloads. They require typed PG identity, Focus projection, and market-fact owners. The successor BFF no longer opens the dated membership file and returns an explicit missing-PG-owner error when the new authority is absent.
- Added a 266-row matrix at `docs/upgrade/V4_R21_CALLSITE_MIGRATION_MATRIX_R1_20261017.json`. It links 244 callsites to exact `V4-NCFR-*` IDs by normalized caller path and line. Twenty-two callsites have no exact edge at that key and remain explicitly unmapped; no IDs were fabricated. Each row records the baseline function, reachability evidence, proposed PG mapping, and current status.
- Code-level status in the matrix: 21 PG-only read paths implemented pending inventory reconciliation, 8 retained publisher/ingress reads still open, and 237 untouched callsites. The formal P1 count remains 266 until the inventory is reconciled; the matrix is not a severity downgrade or live PG acceptance.
- Targeted no-live-PG regression selection: 27 passed. One PG-writer integration case was excluded because no `V4_NATIVE_PG_DSN` is configured; no PG connection or DDL/DML was attempted. After this code batch, push CI run `39003908041` and PR CI run `39003912571` both passed admission, PG candidate validation, and the standard CI business-code file-access check on `2a887a146b133d52068d929956b9f805126ef43a`. These checks do not constitute live PG readback or production acceptance.

## Remaining R21 gates

| Work package | Current disposition | Evidence needed to close |
|---|---|---|
| 200 Owner reads / 52 source files | PARTIAL; 21 code paths implemented, 8 source-ingress paths retained; formal count unchanged | Per-callsite Owner contract and relation mapping; same-T0, source digest, namespace, publication/revision and completeness proof; inventory reconciliation; live PG readback |
| 28 other business reads / 21 files | OPEN; not addressed by this batch | Exact publication-bound relation and consumer field mapping; explicit DEGRADED/BLOCKED behavior; no file fallback |
| 38 external market-data reads / 11 files | OPEN; 0 migrated in this batch | Distinguish ingress from consumers; source manifest, first-available timestamp, original SHA, calendar and authorized PG-ingestion plan |
| 331 dynamic write destinations | OPEN; not classified in this batch | Call-chain and output-purpose evidence for business state, process state, logs and temporary output |
| 52 configuration reads | OPEN; not classified in this batch | Per-input identity and invariant/environment role; `config/` path alone is insufficient |
| 58 stale policy identities | OPEN; not re-audited | Confirmed runtime loader-chain evidence; preserve accepted Head and identity |

Existing publication readers cover only documented Owner families and accepted Publication rows. The matrix provides an exact edge crosswalk for 244 of 266 rows; 22 remain unmatched and need source-edge review. It does not claim that a reference ID by itself proves runtime use or migration.

## Acceptance boundary and next work

This is a code partial result, not `CODE_PASS` for R21 and not V4 production readiness. The formal P1 counter remains 266 pending inventory reconciliation. No compliant live PG Reader identity was supplied, so live PG readback is unverified; no new schema was executed. Next: reconcile the 21 implemented callsites against a fresh targeted business inventory, map the 22 unmatched source edges, then continue the other Owner and business consumers in dependency batches. Any isolated or production PG DDL/DML, accepted Head change, or 28765 deployment remains separately gated.
