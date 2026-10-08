# Workspace cleanup and Git delivery — 2026-10-08

## Contract and scope

Contract: `WORKSPACE_CLEANUP_V1`. This is user-authorized disk maintenance and code preservation, not scanner development, release acceptance, or permission to enter another gated stage.

Applicable controls reviewed: repository `AGENTS.md`; the current V4-only final-blocker audit and scope correction; the target-version online-event redesign plan; Titan `WORKSPACE_HYGIENE_POLICY_V1.md`. Production data, configured TDX inputs, snapshot identities, Codex conversation history, credentials, and authentication databases are protected. No business algorithm or database schema was changed.

## Evidence and results

Machine-readable inventory, deletion plan, deletion ledger, historical worktree disposition, archived Titan Git heads, and summary are under `docs/evidence/workspace_cleanup_20261008/`. The original full disk inventory remains at `G:/codex-maintenance/20261008/inventory.json`.

- Inventoried and processed 1,129 explicitly bounded derivative/cache roots; 1,128 are absent after processing, one is partially removed because Windows denies access.
- Removed E/F/G `codex_tmp`, obsolete clean-checkout copies on E/G, regression outputs, pytest/bytecode/parser caches, and disposable restore/migration/manual-delete backups. Estimated aggregate recovery is 296.28 GiB; the summary distinguishes measured free-space changes from worktree inventory estimates.
- Before deleting registered historical worktrees, confirmed their commits are contained in remote refs. Saved the three modified historical report diffs separately; they do not modify accepted receipts or imply new acceptance.
- Retained the C: `f46d` worktree because a saved Codex conversation still references it.
- Titan current code commit `2beaf3c77ec490c910e61056d5455816e4e6c8b5` was pushed. Four otherwise-unreferenced historical portable heads were pushed to private `codex/archive-cleanup-t5_portable_b*` branches, without merging them into the active branch.
- Football project current code `1561b3f5b73cec64876a5241a625105a87f2c9e8` was already synchronized; its push returned `Everything up-to-date`.
- Lottery project code, rules, and templates were initialized and pushed to private `NanOns/lottery-research`, branch `codex/initial-code-backup`, commit `92779ae`. Its SQLite database, original workbook, and frozen per-issue records remain local and untouched.
- Previously untracked FEP design/audit source materials are preserved in this delivery. Vendored parser dependencies and temporary databases are excluded; `tmp/` and `artifacts/**/parser_deps/` are now ignored.

## Verification and outstanding items

Titan `workspace_clean.py --scan` ran before cleanup and `--verify-root` returned `PASS` afterward. No business tests were rerun because business source behavior did not change. Git delivery does not establish external release acceptance.

Cleanup acceptance is **PARTIAL**, with three explicit exceptions:

1. `E:/codex work/titan_collector/_codex_workspace/quarantine/pre_ws01_tmp/pytest`: Windows access denied. An administrator-only cleanup script is supplied outside the repository.
2. `E:/titan_recovery`: automatic approval rejected deletion; four historical Git heads are already archived remotely. Local copies remain, approximately 0.94 GiB.
3. Old `.codex/..codex-global-state.json*.tmp-*` files: automatic approval rejected deletion. The tool did not return a detailed reason.

Next authorized action remains finishing offline E-to-G path migration after closing Codex. `E:/codex work` is still the authoritative workspace; do not delete it before rebinding and verifying the existing conversations. No next development stage is opened by this maintenance task.
