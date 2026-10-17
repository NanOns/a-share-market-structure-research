---
stage_id: V4_R21_R3_PG_CONTRACTS_AND_MARKET_PATHS_20261017_R1
task_contract: Drive 1Z2YZoDTa9kOJMk-50Gqxyn9i2_vN117E, R3 (2026-10-17)
baseline_branch: codex/v4-workspace-cleanup
baseline_sha: 7f176c136da92376a9225dc8716e61b162391d08
status: R21_R3_CODE_PARTIAL_PATHS_AND_REGISTRY_DRAFT
formal_business_file_p1_before: 266
formal_business_file_p1_after: 266
live_pg_readback: NOT_RUN_NO_COMPLIANT_READER_DSN
pg_ddl_dml_contract_import_head_switch_production_deploy: NOT_AUTHORIZED_AND_NOT_RUN
next_stage: reconcile and migrate remaining publication-bound Owner, business authority, and contract consumers; then rerun focused CI and update Issue 2 / Draft PR 3
---

# R21-R3 implementation report

R3 formally supersedes R2. This batch advances the coding scope and does not claim completion or production acceptance.

## Implemented

- Central market-data path resolution now follows explicit argument, environment, then `config/paths.yaml`; supported settings cover TDX source, daily download and snapshot roots, BaoStock download and cache roots, and ingest temporary files. Relative settings resolve from the repository root. The historic `tdx.root` remains a read-only compatibility alias.
- Removed the runtime `D:/new_tdx` default from the edited official-package, BaoStock daily capture and runtime-manifest readers. The official TDX package, local snapshot CLI, daily executor, BaoStock capture CLI, and operational acquisition path use configured roots. TDX outputs remain guarded outside the read-only source root. Package/capture receipts record the selected path configuration source.
- Added a publication-bound PG contract byte reader. It verifies exact `(contract_id, version, raw_sha256)`, approval, namespace, and original content digest; rejects XML DTD/entity declarations; and fails closed when the publication binding or registry is missing. It opens no local contract file and relies on the caller's single read-only repeatable-read transaction.
- Added a single registry migration SQL draft under `docs/upgrade/`. It stores original bytes and SHA-256, contract format/schema/namespace/approval metadata, append-only versions, and binds versions to existing `v4.publications`. It creates no separate Head and was not registered for execution or applied.

## Scope still open

- The accepted R20/R21 inventory remains at 266 P1 callsites: Owner 200, other business authority 28, market-data source 38. No row is removed or reclassified by this batch. The existing 266-row matrix and 22 unmapped reference edges remain open pending reconciliation.
- The generic reader and SQL draft are not yet wired across all current V4 contract, Owner, Head, descriptor, gate, and source readers. Existing runtime JSON/XML consumers and BaoStock request-ledger persistence require further publication/Owner mapping and migration work.
- The two broader DM-01 orchestration scripts remain unchanged in this batch: repository admission rejects their changed blobs while they read/write operational authority beneath `reports/v4_dm01`. Move those mutable facts to existing PG Owners/publications and retry the orchestration-path change with that migration.
- No live PG catalog or data readback, migration compile, contract registration, business-data write, Head CAS, market-source request, scheduler, or service/deployment action was performed. Seven-page truth and performance remain separately unverified.

## Acceptance and next work

The focused V4/path/PG-shaped suite passed **84 tests**. `compileall` and `git diff --check` passed. These are offline code-path tests, not evidence of registry migration execution or live PG acceptance. The formal P1 denominator stays 266. Continue by mapping each active publication-bound contract and mutable authority consumer to its existing PG relation and exact fields, prioritize the 28 other-business reads and contract files, then resume Owner and ingress batches with per-callsite evidence. No work in this report authorizes PG DDL/DML, actual contract imports, Head switching, or production deployment.
