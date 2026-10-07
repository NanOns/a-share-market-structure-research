# AUDIT_DM01_R4_LEGACY_TEST_ACCEPTANCE_STATE_20261007

Status: OPEN_P2. Independent cross-cutting test-governance audit item; outside R2 IA-03/04/10 fixes.

Scope: tests/v4_dm01_r4/test_runtime.py::test_current_real_v2_parent_and_future_wait expects a post-close 2026-10-08 request to raise PENDING_DM01_R4_EXTERNAL_ACCEPTANCE. Current accepted envelope data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json is EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME and carries R4R1/R4R2 independent acceptance. Consequently the old pre-acceptance expectation fails without any R2 module being imported.

Evidence: reports/forward_repair_r2_20261007/BASELINE_DM01_LEGACY_TEST_RECEIPT.json and .log bind the exact baseline test, implementation, calendar, data head, acceptance head and registry contract. AFFECTED_FAILURE_CLASSIFICATION.json matches the only full-run failure node/message to the isolated baseline reproduction. The full affected run is not green; this failure is not a skip or PASS.

Disposition: preserve old test and accepted runtime/head bytes. Do not revoke acceptance, weaken source/R25 gates, alter numerical kernels, or repair this unrelated debt during R2. IA-05/06/07/08 remain independently OPEN as before. No accepted Current Audit Head is changed; this is an additive audit register entry.

Independent acceptance requirement for a later authorized task: version the historical pre-acceptance fixture separately from current accepted-runtime coverage; demonstrate both fail-closed missing-authority and accepted-envelope behavior, with exact immutable authority bindings. Independent review must close this item; R2 candidate completion or Git push does not close it.
