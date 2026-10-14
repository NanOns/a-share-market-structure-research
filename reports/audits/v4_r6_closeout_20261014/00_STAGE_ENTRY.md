# V4 R6 stage entry — 2026-10-14

## Contract

- Task contract: `V4-R6-PRODUCT-CLOSEOUT-CUTOVER-20261014` / R1 (user-supplied execution card).
- Frozen source baseline: `codex/v4-r4-closeout-20261014` at `174ac59c94a8ac6e27b651036f3860c2226dd9c8`.
- Latest applicable repository upgrade guidance reviewed: `docs/upgrade/V4_INCREMENT_IDENTITY_PARITY_AMENDMENT_R1_1_20261013.md`, plus the 2026-10-13 current native Snapshot/Joint and auto exact-daily continuation contracts. The user-supplied R6 card is the controlling stage scope for this run.
- Applicable guardrails: root `AGENTS.md`; `D:/new_tdx` and configured TDX sources remain read-only; new workspaces and temporary files stay on G:; no `auto_daily` activation; preserve unrelated worktree changes.

## Initial evidence

- Baseline worktree was already present at `G:/codex work/v4-r4-closeout-20261014`; HEAD exactly matches the frozen commit and the worktree was clean. The current chat worktree is a different branch with unrelated modified/untracked files and is left untouched.
- Existing production listener: `127.0.0.1:28765` responds HTTP 200 at `/api/v4/context`. It is served by PID 34284 from `G:/codex work/v4-production-20261012/versions/V4_PACKAGE_1.0.0_88cc19deae3b/DaAV4/DaAV4.exe`; PID 42328 is its daily-worker process. `auto_daily` must remain paused.
- Candidate processes exist on 28768–28770. Their read-only preview results are not production acceptance.
- Latest R5 evidence in `reports/audits/v4_ux_r4_closeout_20261014/` records X01 conflicting identity semantics, X02 stale `NOT_DUE`, X03 exact Joint source byte mismatch (2,020 B / `1d523251...` versus 2,032 B / `839f2852...`), X04 missing production R2 authority, X05 2026-10-12 date lookup failure, X06 reconstructed Focus rows not AS_RECORDED/PIT/admitted, and X07 no new-package HTTP evidence. R5 overall state remains `V4_PRODUCTION_CUTOVER_BLOCKED`.
- No credentials were printed or copied into this record. No production files, Heads, authorities, services, or scheduled tasks were modified during stage entry.

## Acceptance and next work

- Stage-entry acceptance: `PASS` (scope and frozen baseline verified; no product acceptance implied).
- R6 product acceptance: `NOT_ACCEPTED`.
- Next: resolve X01/X02/X03/X04 and implement B1–B5 contracts; then perform T1–T8, candidate-source verification, controlled production cutover, restart/readback, final audit, and required delivery synchronization. Preserve the current package and Heads until every pre-cutover gate passes.
