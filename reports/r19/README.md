# R19 final evidence

Baseline: f4ad7d632e53734798c064f011e2b53ecd99bc27.
Tested implementation source: 3bec750b67e90a281ee70220916da9f105947066.

R19A promotion, R19B/R19C contract freeze and R19D integration passed locally. The unified package is PASS_READY_FOR_EXTERNAL_AUDIT, not externally accepted. Stage Head is V4-14; Data Head remains 2026-09-30. Historical PIT effectiveness remains NOT_GRANTED. V4-15 runtime and Accepted Head are absent. Production, Shadow and Focus remain false.

Clean regression: 1168 retained upstream/replay/rollback tests on the exact audited prepromotion baseline, plus 62 promotion/contract tests on the final candidate. Zero failures, errors, skips or deselections. Historical business code, tests, full_dag_r5, pre-call consumption and rollback blobs are identical. No current-pointer legacy runtime compatibility is claimed; see separate OPEN audit R19-AUDIT-02. Byte portability remains separately OPEN under R19-AUDIT-01.

The initial candidate test failure and its disposition are retained under attempt_01. Final code extends deterministic, exact-hash representation restoration to explicitly bound contract sources; no historical policy is rewritten. Each detached context is clean before and after testing, with no assume-unchanged or skip-worktree flags. Unchanged baseline evidence was reused after the candidate-only correction; its original complete XML/log/gate are preserved.

TESTED_SOURCE.bundle retains the exact tested source commit and tree without adding an intermediate commit to the branch. The bundle requires the audited baseline already in repository history. Reproduction:

```powershell
git bundle verify reports/r19/TESTED_SOURCE.bundle
git fetch reports/r19/TESTED_SOURCE.bundle refs/codex/r19-tested-source
python -m scripts.validate_r19_clean_detached 3bec750b67e90a281ee70220916da9f105947066 '<external-output-directory>'
```

The final branch commit adds evidence only relative to the tested candidate. The runner discloses both validation contexts and verifies exact retained source identities. Formal DB migration is never applied. Only existing disposable regression fixtures use test databases.

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT.
