# V4-08 R5.1 stage entry

Contract: docs/evidence/V4_08_R5_1_THREE_BLOCKER_TARGETED_REPAIR_TASK_20260930.md; latest applicable baseline REV4 FEP R2 plus accepted scoped amendments. Input HEAD 10d500ce51a9a0914c0d812c1c1fee761c5a3af9.

Scope: R5-B01 semantic/rank provenance; R5-B02 accepted raw amount; R5-B03 accepted price identity. Accepted parameters, membership, midrank, four-state evaluator and migration 020 preserved. No scanner entry or TDX writes. Existing unrelated FEP worktree inputs excluded from this change.

Evidence: source producer mapping, frozen SHA dependencies, isolated accepted-source adapter fixtures, real 2026-09-30 fail-closed materialization, no-symbol scan, clean detached PostgreSQL regression.
Acceptance: IN_PROGRESS; engineering candidate only. Next: independent external reaudit; no V4-08 global promotion or production permission.
Independent OPEN audit items remain Prior-RPS bootstrap, AUD-AMOUNT-A-06, target Core availability and V4-01 dated roster; none is closed by this gate.

Standing user agreement (2026-09-30): after each authorized stage completes, commit and push its relevant code and evidence to Git; avoid unrelated worktree changes.
