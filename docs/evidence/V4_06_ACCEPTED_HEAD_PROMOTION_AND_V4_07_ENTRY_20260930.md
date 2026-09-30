# V4-06 Accepted Head Promotion and V4-07 Entry — 2026-09-30

## Stage contract and evidence

- Stage: `V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930`.
- Starting global pointer: `6fd6e16b3769726f14e44b1d2062d087fd40ec1ede51956a5353631896547043`; V4-05 Accepted Head remains `fc929d85553a900a6479ac9f50291d50cf750ad0e6c21fc58e4e05e92189f5cb`.
- V4-06 candidate manifest: `5d9297b324c57d66228f66b5e291b4cca2b8ca4325d92759676401b1f6352b14`; all 22 listed files and byte counts independently match.
- Implementation commit: `4c6051586a617d01f2ebbe142ea4ded05660fec7`. Migration 013 identity is preserved; migration 014 `fff140f483738b6fb8e94e06a4e2c681111de94ceb1c415d18c188a9d95977e3` applied and isolated rollback passed.
- External decision source: `V4_07_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE_20260930.md` (SHA-256 `082ebdecc7efd45a643a6b887250436c0bcac796c59178de4a8d19e37191296c`), decision `V4_06_EXTERNAL_ACCEPTANCE_PASS_R2_SCOPED_DEGRADED`.

## Acceptance result

`V4_06_ACCEPTED_HEAD_PROMOTION_PASS_R1` — `DEGRADED_PASS`.

`BAOSTOCK_LIVE_STRICT_BINDING = BLOCKED_DEGRADED`. Audit `V4-06-BAOSTOCK-BINDING-TOLERANCE-01` remains `OPEN`; its tolerance and denominator semantics are not inferred. All V4-00 through V4-05 global bindings were checked for preservation.

Accepted Head: `reports/v4_06/V4_06_R2_STAGE_CANDIDATE_MANIFEST.json` is bound by `5aec962703aed40cab809e798edc5bfbe50c416809984db40bb679a172782f8e` at `data/v4/V4_06_ACCEPTED_HEAD.json`.

## Next stage

After the promotion validation passed, the global accepted range advances through V4-06 only. Next is V4-07 Accepted Head promotion under the independent R2 engineering-scope acceptance. V4-08 remains blocked pending an accepted PIT membership baseline and reconstruction; BaoStock strict binding remains separately audited.
