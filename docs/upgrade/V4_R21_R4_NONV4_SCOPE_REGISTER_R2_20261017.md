---
stage_id: V4_R21_R4_NONV4_SCOPE_REGISTER_R2_20261017
baseline_head: 894df4fc4429258751f703f94bc6c3865a30e723
status: REVIEWED_NO_NONV4_FUNCTIONAL_CODE_MODIFIED
---

# R21-R4 non-V4 scope register (R2)

## Boundary

This register applies the R2 execution-card rule that discovering a reference does not authorize changing its owner. Only current V4 runtime capabilities and direct R21-R4 dependencies may be changed. Non-V4 paths below are recorded for disposition only. No V1/V2/V3, M14, retired algorithm, or unrelated business functionality was changed, repaired, tested, or cleaned up in this batch.

## Observed paths

| Path / evidence | Classification | V4 reachability evidence | Disposition / possible V4 blocker |
|---|---|---|---|
| `src/focus_tracker/v4_daily_driver.py` (`V4-BCA-R2-10a48324e85797ed4c8b`; reference IDs `V4-NCFR-0159470`, `V4-NCFR-0159471`) | SCOPE_UNRESOLVED; paired reference edges are `OUTSIDE_V4_SCOPE` | Baseline matrix points those edges to `v4_repo_scan`; no current V4 service/daily entrypoint was established by the edge evidence | No edit. If a current V4 caller is later proven, migrate only its V4 adapter. Otherwise retain as unresolved/out-of-scope; no blocker can be inferred from a scan edge alone. |
| `src/focus_tracker/v4_native_core_daily_driver.py` (`V4-BCA-R2-431072db33876382013a`; reference IDs `V4-NCFR-0159484`, `V4-NCFR-0159485`) | SCOPE_UNRESOLVED; paired reference edges are `OUTSIDE_V4_SCOPE` | Baseline matrix points those edges to `v4_repo_scan`; no current V4 service/daily entrypoint was established by the edge evidence | No edit. Potential V4 blocker remains unproven. |
| `src/v4/replay_inputs.py` (`V4-BCA-R2-97c1bd0ed538b4e13a26`; reference IDs `V4-NCFR-0159693`, `V4-NCFR-0159697`) | SCOPE_UNRESOLVED; paired reference edges are `OUTSIDE_V4_SCOPE` | Baseline matrix points those edges to `v4_repo_scan`; no current V4 service/daily entrypoint was established by the edge evidence | No edit. Potential V4 blocker remains unproven. |
| `src/v4/target_fact_producers_r3.py` (`V4-BCA-R2-30b53176558c40e5aba6`, `V4-BCA-R2-1ce6a6e14046e644b99b`; reference IDs `V4-NCFR-0159740`–`V4-NCFR-0159743`) | SCOPE_UNRESOLVED; paired reference edges are `OUTSIDE_V4_SCOPE` | Baseline matrix points those edges to `v4_repo_scan`; no current V4 service/daily entrypoint was established by the edge evidence | No edit. Potential V4 blocker remains unproven. |
| `.github/workflows/repository-policy.yml` | Repository-level automation, direct task dependency | The sole workflow contains repository admission plus V4 focused tests and file-access audit; it is not V4 business functionality | Only automatic `push`/`pull_request` triggers were removed at the user's direction. `workflow_dispatch`, all job definitions, and `tools/git_repository_policy.py` are retained. Local admission remains mandatory. |
| `.githooks/pre-push` | Git LFS transport hook | Executes `git lfs pre-push`; it is not a GitHub CI test or a business consumer | Preserved unchanged so LFS transport continues to work. |

## Result

No non-V4 functional module or old-version test was changed. The five matrix paths above remain `SCOPE_UNRESOLVED`; they are not reclassified as retired and do not close any of the 266 stable callsite IDs. The R2 workflow change stops automatic GitHub Actions test/scan execution while preserving manual workflow execution and all local checks.
