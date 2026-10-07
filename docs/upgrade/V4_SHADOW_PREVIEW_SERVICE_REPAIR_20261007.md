# V4 Shadow preview startup repair — 2026-10-07

Stage contract: `V4_SHADOW_PREVIEW_SERVICE_V1`. User authorized service startup for manual V4 acceptance, then startup repair.

Applicable authority: `docs/evidence/r26/V4_17_R26_SHADOW_UI_ENGINEERING_TASK_20261004.md`, `config/v4_17_shadow_ui_contract_v1.json`, `config/v4_17_shadow_ui_source_v1.json`, and `docs/audits/V4_00A_DATABASE_RESET_AUDIT_20260925.md`. The existing R26 engineering boundary and absence of real readback acceptance remain binding.

Root cause: the unified launcher runs legacy publication recovery before HTTP startup. The clean V4 database intentionally contains no `workbench` schema; startup failed with UndefinedTable for workbench.jobs. Recreating legacy data would contradict the accepted reset boundary.

Repair: explicit `--v4-shadow-only` mode uses the existing standard-library HTTP server and existing ShadowContextReader, static page, and script. It never initializes legacy recovery, production writers, or legacy database adapters. Invalid Shadow contracts prevent startup. Only read routes are served; POST/PUT/PATCH/DELETE return 405. The ordinary launcher retains its existing behavior.

Run from repository root: `E:/python/python.exe run_workbench_service.py --v4-shadow-only --host 127.0.0.1 --port 28765`.

Evidence: `reports/manual_v4_preview_20261007/service_receipt.json`; 44 existing Shadow UI tests passed with basetemp E:/codex_tmp/test_temp/manual_v4_preview_20261007; 1 new regression passed with basetemp E:/codex_tmp/test_temp/manual_v4_preview_regression_20261007. The new regression forbids psycopg and DuckDB connections and exercises page access, no-data context, all four rejected write methods, duplicate parameters, and unavailable legacy routes. Initial test attempts used unsupported temp paths and failed before execution; rerunning in the declared disposable root passed. `git diff --check` passed.

Acceptance: `PASS_SERVICE_ACCESS_ONLY`. Live HTML and JS return 200; context returns honest NO_REAL_SHADOW_DATA; status is READY / V4_SHADOW_ONLY. No PostgreSQL schema or data was changed; no accepted heads or TDX inputs were changed. No real Shadow sample, V4-17 final acceptance, default UI cutover, or next-stage permission is claimed.

Next: user manual acceptance at http://127.0.0.1:28765/v4/shadow. Real-data display remains gated by independent accepted readback configuration. Page links to V3/Focus are unavailable in this explicit preview mode.
