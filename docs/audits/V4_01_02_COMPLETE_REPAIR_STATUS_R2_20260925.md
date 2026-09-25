# V4-01 / V4-02 R2 Repair Status (2026-09-25)

## Governing contract and user direction

- Latest applicable upgrade: `DA-MSR-V4.2.2-CODEX-REV2`, SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`; repair scope follows the supplied `V4_01_V4_02_COMPLETE_REPAIR_AND_BAOSTOCK_INTEGRATION_R2_20260925.md` (`DA-MSR-V4-01-02-COMPLETE-REPAIR-R2`).
- Stage contracts: V4-01 `V4_TDX_HISTORY_BOOTSTRAP_V1` plus R2 §§3B.1–3B.6/§78; V4-02 `V4_CANONICAL_DAILY_PIT_PERIODS_V1` plus §§3B.6/3C.1–3C.4/5.2–5.3/6A/10N/78; BaoStock supplemental `BAOSTOCK_SUPPLEMENTAL_SOURCE_V1`.
- User completion rule: do not call a stage complete in a degraded state without repeated human and programmatic verification. Accordingly this repair status does not use `DEGRADED_PASS` as a completion result.
- TDX roots are read-only inputs. No TDX files, database rows, scanners, factors, or trading paths were touched.

## Result

**V4-01: `BLOCKED / R2_REPAIR_OPEN`. V4-02: prior run `SUPERSEDED_CANDIDATE`; R2 completion remains blocked. BaoStock: implementation added, live capability `UNAVAILABLE_PENDING_INDEPENDENT_ACCEPTANCE`.**

The previous receipts and their large local Parquet outputs were not overwritten or deleted. The prior `V4_01_TDX_HISTORY_BOOTSTRAP_20260925` and `V4_02_CANONICAL_DAILY_PIT_20260924_085207Z` `DEGRADED_PASS` claims do not satisfy R2 completion criteria.

## Completed repair work

1. V4-01 now records per-file byte counts and SHA-256 values in a new R2 inventory, and records the same content-addressed snapshot digest. The new R2 manifest and receipt use new paths so earlier evidence remains immutable.
2. V4-02 now requires a `FULL_PASS` V4-01 receipt. It independently compares ZIP member names, member bytes, extracted file sizes/hashes, the V4-01 inventory, and the content digest before canonical processing. Unsafe paths, duplicate members, modified files, and archive/extraction drift fail closed.
3. Canonical schema separates `source_security_key` from nullable `canonical_security_id`; filename identity is no longer promoted to canonical identity.
4. V4-01 and V4-02 stage receipts now return `BLOCKED` while R2 identity, lifecycle/PIT, source-priority, adjustment, period, and historical price-limit evidence is missing. No scanner or factor stage is authorized by these artifacts.
5. BaoStock SDK `0.9.4` was installed in the base runtime. Its official PyPI wheel SHA-256 is `0bf71c6069ab5890ff3596632f9c3f8f1fbc6bfcac582c2f9d6a5c11ab2cfaf8` (corrected in R3; the earlier recorded digest had a typo). The inspected SDK exposes `set_API_key()` and routes `bs-` API keys to `vip-api.baostock.com`; this verifies SDK wiring, not the supplied account's live credentials.
6. BaoStock adapter reads credentials only from process environment, counts login/query/retry/logout, allows one SDK session, sets 30-second socket timeouts, serializes requests, writes a secret-free request ledger/checkpoint, and persists only rows whose binding callback returns `BOUND_STRICT`. Without independently accepted tolerance evidence, binding stays `BOUND_SOFT` or `UNBOUND`.
7. Field map `BAOSTOCK_FIELD_MAP_V1` records official documented semantics: daily `turn` is percent points and is normalized by `/100`; its denominator is circulating shares, not free-float shares. `volume` is shares, `amount` is CNY, `tradestatus` is a cross-check, and suspended daily records may show previous close with zero volume/amount. BaoStock remains supplemental and cannot replace TDX prices.
8. The configured `D:/new_tdx` root was read only. Its `vipdoc/{sh,sz,bj}/lday/*.day` inputs were copied into a project-owned content-addressed snapshot (12,245 files; 941,724,256 bytes). The complete snapshot was re-hashed and verified; V4-01's source manifest and receipt bind both the snapshot content digest and manifest SHA-256. No snapshot data or writes were placed under the TDX root.
9. V4-02 now emits an explicit R2 blocked-entry receipt when its required V4-01 `FULL_PASS` is absent, recording the exact V4-01 receipt hash and execution identity; it emits no canonical outputs in that case. The current receipt is `reports/v4_02/v4_02_stage_receipt_R2_20260925.json` and reports `BLOCKED`.

## Verification evidence

- `python -m pytest tests/v4_phase0 -q`: **82 passed, 1 skipped** (Windows symlink fixture skipped because this environment cannot create the required link).
- `python -m compileall -q ...` and JSON parsing of the BaoStock contract: **passed**.
- Re-ran V4-01 into a new R2-named report set: all 12,438 `.day` files / 29,768,339 records inventoried; 60-session A-stock overlap report remains accepted; 18 malformed/non-core files were retained; stage receipt is **BLOCKED**, not complete.
- Re-ran V4-01 after binding the verified local snapshot: snapshot verification is `PASS`; its manifest SHA-256 is recorded in the R2 receipt; V4-01 remains **BLOCKED** on source selection, canonical identity, historical lifecycle/PIT, adjusted-history empirical acceptance, AS_RECORDED, and retained malformed/non-core inputs.
- Invoked V4-02 under the R2 contract: it stopped at the mandatory V4-01 entry gate and emitted a hash-bound `BLOCKED` receipt without writing canonical or period datasets.
- Independent V4-02 postcheck verified the source ZIP against every extracted member and verified all three old Parquet hashes, byte counts, and metadata row counts. The postcheck is `SUPERSEDED_CANDIDATE` because the old run receipt is degraded, its V4-01 gate is not full, it predates R2 snapshot binding, and its daily schema conflates source key with canonical identity.
- The new R2 postcheck artifact is `reports/v4_02/V4_02_CANONICAL_DAILY_PIT_20260924_085207Z_r2_postcheck.json` (local ignored evidence; can be force-added with the related small receipt artifacts after this repair is complete).
- Four bounded live probes were made through temporary process-only credential injection. All four login/logout cycles succeeded; three daily-history calls and one single-security basic-data call returned provider error code `10001015`. The request ledger records 12 requests in total, including login and logout. The current Codex process has no credential environment values after the runs. Credentials from chat were not copied into code, configuration, logs, or receipts. API_KEY routing and login are verified; no BaoStock data query is operational, so the capability remains blocked. Further probes were stopped after both a historical query and an independent basic-data query returned the same error.

## Open acceptance work

- R2-02/03: accepted local-TDX versus package source-selection manifest and source-key/canonical-ID mapping.
- R2-04/05: dated historical lifecycle facts and `historical_evaluable_universe(t)` with reproducible digest.
- R2-06/07: new RAW canonical rebuild with accepted adjusted-coordinate real-action samples (cash, split/stock, rights, combined, unknown, halt/resumption, recent IPO, no-action) and no future leakage.
- R2-08/09/10: formal versioned calendar, `CLOSED_ONLY`, `AS_OF`, and §3C.4 physical-truncation temporal-leakage proofs.
- R2-11: authoritative effective-dated `PRICE_LIMIT_RULE_V1` table and independent samples; no inference from BaoStock or prior close.
- R2-12/14/15: BaoStock login/API_KEY authentication succeeded four times, but both history and basic-data queries returned `10001015`; representative multi-board/status/date responses, measured coverage, and independently accepted BaoStock-specific tolerances are still missing. Until then no `BOUND_STRICT` production dataset.
- R2-16/17/18/19/20: historical supplemental bootstrap, checkpoint/idempotency/retry/budget/circuit-breaker postchecks, cross-source reconciliation, commit/script identity, and final capability gate.
- Independent audits `V422-B01`, `V422-B03`, `V422-B04`, `V422-B07`, `V422-B08`, `V422-B10`, and `AUD-AMOUNT-A-06` remain independent and OPEN.

**Next:** resolve BaoStock provider error `10001015` with the provider/API-key entitlement, then rerun the bounded live smoke receipt only after capability becomes queryable. Continue the V4-01 source/identity/PIT and V4-02 adjusted/calendar/period repairs; do not advance to V4-03 or declare completion while any required gate above is open. Online-model acceptance remains external to this local evidence.
