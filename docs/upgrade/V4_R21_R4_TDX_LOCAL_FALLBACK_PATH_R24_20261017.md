stage_id: V4_R21_R4_TDX_LOCAL_FALLBACK_PATH_R24_20261017
baseline_sha: b0fd21b0058a154e56911ed4007885f5a4e549ec
branch: codex/v4-workspace-cleanup
status: TDX_LOCAL_FALLBACK_CONFIGURED_SOURCE_PATH_CODE_COMPLETE_INGEST_OPEN
callsite_ids: V4-BCA-R2-d85b9178c81b9f1f62fe; V4-BCA-R2-b27ea1de27ada027ba55; V4-BCA-R2-99269cbe5cf6215f9d67; V4-BCA-R2-f6c8d8313ae78fe2a109
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact TDX/BaoStock source contracts, PG append and same-T0 consumer wiring
---

# V4 R21-R4 configured TDX local fallback path

Date: 2026-10-17 (Asia/Shanghai). This batch continues the R21-R4 source-path audit across the 38 external market-source callsites.

## Code change

- `tdx_local_daily_fallback_v1.fallback` no longer defaults to the literal `D:/new_tdx` path. It now resolves the TDX source root using explicit argument, `TDX_ROOT`, then `config/paths.yaml` through the existing central resolver.
- The fallback receipt records the resolved TDX source root and which configuration layer selected it.
- Native bars remain read-only ingress inputs. The composite/package and receipt are written to the configured caller snapshot root, and the existing outside-source-root boundary still applies.

## Exact callsite and accounting

- Matrix IDs: `V4-BCA-R2-d85b9178c81b9f1f62fe`, `V4-BCA-R2-b27ea1de27ada027ba55`, `V4-BCA-R2-99269cbe5cf6215f9d67`, and `V4-BCA-R2-f6c8d8313ae78fe2a109`.
- These rows now have precise path-configuration and test evidence; they remain OPEN because no live source package was ingested, no approved PG source fact was appended, and no same-T0 accepted publication readback occurred.
- Original baseline: **266**. Formal completion: **0 / 266**. Formal remaining: **266**. This batch closes no business-read row.

## Verification and limits

- **16 passed** across local fallback, official package and configured-path regressions.
- `compileall`, `git diff --check`, and staged repository policy passed. The tests use isolated source/cache directories and did not read or write the configured TDX source root.
- No network acquisition, PG connection, DDL/DML, accepted Head change, service start or production operation.

## Next stage

Continue exact Source ingress contract-to-PG binding and same-publication consumer reads. Audit the remaining TDX/BaoStock entrypoints for hardcoded roots and resolve each exact callsite ID without lowering the formal denominator on path-only changes.
