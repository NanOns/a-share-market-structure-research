---
stage_id: R21-R4-baostock-capture-contract-pg-consumer-r63
branch: codex/v4-workspace-cleanup
status: BAOSTOCK_DAILY_CAPTURE_FORMAL_SOURCE_CONTRACT_USES_APPROVED_PG_REGISTRY
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22
---

# BaoStock capture contract consumer to PG (R63)

Date: 2026-10-17 (Asia/Shanghai).

## Implemented consumer path

The active `scripts/capture_baostock_daily_update.py` entrypoint no longer reads `config/baostock_supplemental_contract_v1.json` directly. Its `load_source_contract` function calls the existing `_daily_runtime_contract` reader for `BAOSTOCK_SUPPLEMENTAL_SOURCE_V1` version `1.1.0`. The production default requires the approved PG registry, configured model namespace and expected database identity, and the reader's read-only repeatable-read transaction. Missing registry state fails closed; the default path does not fall back to the local JSON file.

## Verification and limits

- Focused entrypoint, registry, and daily-executor regressions: **24 passed**.
- The test verifies the actual capture entrypoint delegates the exact contract id/version/namespace path to the PG runtime-contract reader. Existing registry tests cover latest approval/revocation, source revision, content digest, database identity and read-only transaction guards.
- Push CI run [39023921836](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39023921836) and PR CI run [39023924531](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39023924531) both completed successfully.
- No live PG read/catalog, BaoStock network request, runtime smoke, PG write, or DDL/DML ran. The per-day BaoStock runtime acceptance manifest, native response and smoke receipt are still local source-ingress payloads and remain open for migration.

## Original 266-item accounting

No original baseline callsite ID was modified in this batch, so formal completion remains **0/266**, with **266** formally remaining. Counts remain **48** PG code paths pending live reconciliation, **210 OPEN**, **8 ingress**, **218** open or ingress, and **22** unmapped edges. The runtime acceptance manifest/response is not credited as migrated by this contract-only change.

## Next

Continue the actual per-day runtime acceptance/source-response ingress into a typed PG Owner relation, then migrate operational Head reads after an accepted Head mapping is established. Do not count the capture contract reader as full BaoStock or end-to-end business acceptance.
