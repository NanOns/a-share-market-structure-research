---
stage_id: V4_R21_R4_R2_LOCAL_V4_PROGRESS_20261017
branch: codex/v4-workspace-cleanup
baseline_head: 894df4fc4429258751f703f94bc6c3865a30e723
status: LOCAL_FOCUSED_V4_AND_REPOSITORY_POLICY_PASS_PARTIAL_CONSUMER_MIGRATION
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# V4 R21-R4 R2 local execution progress

## Scope and applicable records

Execution follows the R2 task card `V4_R21_R4_本地验收及仅V4代码范围强制修订任务_R2_20261017.md`. Before this batch, reviewed the latest applicable repository records: the R97 DM-01 Data Head V2 import/consumer report, R82 Profile correction consumer report, R81 Focus projection BFF callsite report, R80 Owner authority-manifest report, and the R4 contract SQL compatibility and R9 rollback reports. Their evidence keeps the 266-item formal count at 0 closed / 266 remaining until live identity and exact per-ID reconciliation exist.

## Changes in this batch

- Changed `.github/workflows/repository-policy.yml` to `workflow_dispatch` only. Push and pull-request Actions tests/scans no longer auto-run. Workflow jobs and local policy tooling remain intact.
- Added `V4_R21_R4_NONV4_SCOPE_REGISTER_R2_20261017.md`. It records five unresolved/out-of-scope reference paths from the stable-ID matrix, why scan-edge evidence does not prove current V4 reachability, and the no-edit disposition.
- Existing V4 consumer migrations at HEAD `894df4fc4429258751f703f94bc6c3865a30e723` include the R97 DM-01 Data Head V2 PG importer and date/stage-bound daily consumer. The reviewed R97 evidence maps no original stable ID to that new import/runner pair; it changes none of the 266 formal statuses.

## Current baseline evidence

The checked-in matrix `V4_R21_CALLSITE_MIGRATION_MATRIX_R1_20261017.json` has exactly 266 stable rows: 200 Owner, 28 other-business, and 38 market-source rows. Its current recorded status counts are 53 `IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION`, 10 `ACTIVE_INGRESS_ADAPTER_OPEN`, and 203 `OPEN`; 22 reference edges remain unmapped. No live PG identity/readback is available, so **0/266 are formally closed**. The new R97 work does not justify changing any row without an exact callsite and accepted PG binding.

An itemized, read-only reconciliation for **all 266 IDs** was captured at `G:/codex_tmp/v4_r21_r4_r2_callsite_266_894df4.json` (SHA-256 `ed364f4b0197ebfe78b1ddb301542ffc866b031b3c52c8f9b5bdecc21f451a44`). It records each ID's existing status, source path/line, referenced IDs, source SHA at the declared baseline commit, current file SHA/existence and whether the file still matches the baseline. **263/266** baseline file hashes match the Git blob at the matrix's declared baseline commit; **3/266** do not: `V4-BCA-R2-33ff91eb2cc7f9242d1b`, `V4-BCA-R2-d8f1515f20b63e2ab89c`, and `V4-BCA-R2-c53955269a0f76785382`, all in `src/workbench_analysis/historical_stage_governance_r17.py`. That file's baseline Git blob is unchanged through this audit HEAD, so the recorded mismatch is retained for source-owner reconciliation. **107/266** source paths have current bytes different from their baseline bytes; the evidence package identifies them individually. These file identity findings do not establish PG consumer acceptance and do not close any row.

## Local verification

- Command: `python -m pytest --confcutdir=tests -q -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/r21r4_r2_894df4_1017 tests/test_v4_contract_registry_pg_v1.py tests/test_v4_r21_contract_registry_sql_syntax.py tests/test_v4_dm01_daily_stage_consumer.py tests/test_v4_dm01_stage_state_pg_r1.py tests/r4_repair/test_configured_tdx_path.py tests/test_operational_daily_executor_v1.py tests/test_git_repository_policy.py` — **80 passed in 5.48 seconds**. The first collection attempt lacked `pglast`; reused the existing `G:/codex_tmp/pydeps_r21_r4` dependency path for the successful run. No dependency was installed or copied into the repository.
- `git diff --check` — PASS.
- `python tools/git_repository_policy.py --staged` — PASS, 3 changed blobs.
- Pytest log: `G:/codex_tmp/r21r4_r2_local_pytest.log`; SHA-256 `55e5d8aa214cede3b859df430a3c7f748acbfc903625c68045d4dfc13af7490`.
- No GitHub Actions run was triggered or awaited.

These checks verify controlled offline code paths and repository admission only. They do not establish live PG catalog/readback or business acceptance.

No stable-ID row changed disposition in this batch. The 53 code-level PG rows remain pending inventory/live reconciliation, 10 ingress rows remain open, and 203 rows remain open. The R97 importer/runner pair has no exact row mapping, so it closes no original ID. This report points to the canonical 266-row matrix rather than rewriting IDs or counting the same evidence as a closure.

No live PG catalog, DDL/DML, contract import, accepted Head CAS, production service/scheduler, production deployment, or physical deletion is included. Those remain separately unauthorized. No production Head or source-root content is modified.

The R2 read-only catalog prerequisite was attempted through the configured environment contract. `WORKBENCH_PG_DSN` is not configured, so the catalog result is `DB_READ_ENV_UNAVAILABLE`; no connection was opened and no catalog result is claimed.

## Next

Continue the remaining current Head/Owner/other-business consumer migrations, reconcile the exact 266 IDs when source and PG identity evidence is available, and continue TDX/BaoStock source contracts. This batch is partial progress; it does not complete the 228 non-market consumers or 38 source entries.
