stage_id: V4_R21_R4_DAILY_RUNTIME_CONTRACTS_PG_READER_R56_20261017
branch: codex/v4-workspace-cleanup
status: DAILY_RUNTIME_CONTRACTS_READ_FROM_APPROVED_PG_REGISTRY_BY_DEFAULT
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22

# V4 R21-R4 daily runtime contracts PG reader

Date: 2026-10-17 (Asia/Shanghai). Reviewed the official R21-R4 execution card, R49 Registry SQL/schema report, R54 PG-only registry consumer batch, R55 candidate BFF batch and current 266-row matrix.

## Implemented

- Added `load_current_approved_contract` for pre-publication runtime contracts. It reads the exact contract id, version and namespace in the caller's read-only repeatable-read snapshot; verifies the configured database identity and no-write Reader role; selects the latest approval event including revocation; and checks approver, approval reference, source revision and raw SHA against immutable contract bytes. Publication consumers continue to use acceptance-time-pinned `load_publication_contract`.
- The daily executor now loads `V4_DAILY_TDX_READONLY_SOURCE_R1` 1.1.0 and `V4_DAILY_RUNTIME_ACCEPTANCE_PATH_R1` 1.0.0 from the PG registry by default. Missing PG identity, namespace, schema, approved version, current approval or exact bytes fails closed before using either runtime path contract. The old file mode is available only when explicitly selected.
- Added approval/revocation/digest tests and executor wiring tests. Added the Registry test module to repository-policy CI.
- Updated the two exact daily-executor rows in the original callsite matrix; this reduces OPEN rows without changing the denominator.

## Verification and limits

- Focused Registry and daily-executor selection: **32 passed** with controlled PG boundaries.
- No live catalog query, Registry import, PG write, schema change, daily service start, source capture or accepted Head update occurred. Both runtime contracts still require approved registration in the selected PG namespace before the default runtime path can run.
- R55 CI is pending for commit `240ec7135`; R54 CI is green on push and PR.

## Accounting

Original P1 denominator remains **266**: 200 Owner, 28 other-business, 38 external-source reads. Formally complete **0/266**; formally remaining **266/266**. Current matrix: **48** code-level PG paths pending live readback/reconciliation, **210 OPEN**, **8 ACTIVE_INGRESS_ADAPTER_OPEN**, and **22** unmapped reference edges. In the 28 other-business file-read rows, **4** have code-level PG paths, **23** remain OPEN and **1** remains an ingress adapter.

## Next stage

Continue the remaining other-business reads, including runtime Heads and formal contract loaders, then continue the 200 Owner reads and DM-01 state migration. Verify the two runtime contracts' actual approved PG registration and namespace when a compliant Reader is available; do not count mock approval data as acceptance.
