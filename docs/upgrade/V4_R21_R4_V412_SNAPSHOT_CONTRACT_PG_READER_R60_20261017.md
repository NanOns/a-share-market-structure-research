stage_id: R21-R4-v412-snapshot-contract-pg-reader-r60
branch: codex/v4-workspace-cleanup
status: DESIGN_BLOCKER_IDENTIFIED_NO_SOURCE_CHANGE_RETAINED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 47
open_callsite_rows: 211
ingress_adapters_open: 8
remaining_open_or_ingress: 219
unmapped_reference_edges: 22

# V4.12 snapshot contract reader migration audit

Date: 2026-10-17 (Asia/Shanghai). Reviewed the R21-R4 execution card, R59 report, 266-row matrix, existing V4.12/R14 contracts and R59 CI.

## Design constraint found

The two candidate callsites `V4-BCA-R2-0a924f66fca35bcbdca9` (`v4_12_breakout_snapshot.py::load_contract`) and `V4-BCA-R2-bda5b564513151663d58` (`v4_12_frozen_snapshot_v2.py::load_contract`) are pinned by accepted historical SHA evidence consumed by `tests/test_v4_r14_governance_contracts.py`. Editing either module changes its exact source bytes and causes three V4.12/R14 closure tests to reject the accepted historical runtime. In-place migration breaks that accepted closure.

A PG registry wrapper prototype passed 47 focused reader and R12/R13 cases, but the repository-policy selection exposed the pinned-source invariant. I removed the prototype and retained no source modifications or migration credit. Correct continuation needs a versioned replacement runtime/entrypoint and an accepted transition contract that switches current execution while preserving frozen historical readers byte-identically. This is a design boundary, not a missing-PG-credentials issue.

## Verification

- Prototype focused selection: 47 passed, 2 deselected. These are not migration evidence because the production callsite source was reverted.
- Repository-policy selection: 276 passed, 3 failed. All three fail on the same exact-SHA rejection at `src/workbench_analysis/v4_12_breakout_snapshot.py`, proving the source-freeze constraint. The failure is recorded, not reported green.
- R59 push and PR CI passed: `39022160995` and `39022163504`. No R60 source was retained or pushed.
- No live PG read/write, contract import, source capture, service start or Head update occurred.

## Accounting

No matrix status changed. The original denominator remains 266: 200 Owner, 28 other-business and 38 external-market-source reads. Statuses remain 47 code-level PG paths pending reconciliation, 211 OPEN, 8 active ingress adapters, 219 open or ingress, and 22 unmapped edges. Formal completion remains 0/266; formal remaining 266/266.

## Next

Continue an independent source-grounded migration batch. Preserve these V4.12 pinned sources unless a formally accepted versioned-runtime transition is established.
