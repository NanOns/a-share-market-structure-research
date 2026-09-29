# V4-06 R2 Candidate Closure

## Result

- Terminal status: `V4_06_DEGRADED_PASS_CANDIDATE_R2`.
- This is an engineering candidate for independent external audit. No V4-06 Accepted Head was created, and the global accepted range remains at V4-05.
- Starting HEAD: `0f13e1b55d86ee74dfc489a48e95a766111a617a`.
- Implementation commit: `4c6051586a617d01f2ebbe142ea4ded05660fec7`.
- Accepted input: publication `PUB-3c03e227-c60a-4d8c-86ae-2861507c257b`, trade date `2026-09-28`, Core logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`, 5,222 identities.

## Contract repairs and evidence

- S01 PASS: `turnover_pct5/20/60` use the REV2 midpoint empirical percentile formula and `[0,100]` units. Independent vectors return 0, 100, 50, and 70 for all-above, all-below, all-equal, and mixed samples.
- S02 PASS: canonical `turnover_state` uses `turnover_pct60`; all required 20/70/90/97 boundary vectors passed. `turnover_context` is a deprecated exact alias.
- S03 PASS: binding quality is separate from semantic state. Versioned reason mapping produces `PENDING`, `UNAVAILABLE`, or `UNKNOWN_DATA`; the 59/60 sample, unknown-gap, and target-binding cases passed.
- Persisted tolerance schema PASS: tests consume the real `contract_version` schema. The real config remains `BOUND_SOFT` with strict binding forbidden. Negative gates cover wrong contract/source/dataset/version, comparison basis, strict flag, missing independent acceptance evidence/reviewer/timestamp, and wrong denominator basis. Synthetic accepted copies and epsilon boundary rows are explicitly test fixtures, not live acceptance.
- `supplemental_extension_note` PASS: versioned producer/source provenance, accepted Core fact reference, and no Core/PREWATCH/Base Seed/maturity/Focus effects. Missing source truth remains explicit.
- Migration 014 PASS: checksum `fff140f483738b6fb8e94e06a4e2c681111de94ceb1c415d18c188a9d95977e3`; PostgreSQL 18.6 isolated apply/rollback passed. Migration 013 checksum is preserved. The persistence probe accepted percentile 100, rejected 101 and alias mismatch, and left the accepted Core publication head unchanged.
- Core isolation PASS: accepted publication and logical digest before and after the isolated persistence probe are identical.
- Runtime PASS: `python -m pytest tests/v4_06 -q` — 69 passed. Python compilation and `git diff --check` passed.
- Clean checkout PASS: the exact implementation commit was tested in a clean detached worktree. The accepted V4-05 evidence root was supplied read-only because the clean worktree contained an unhydrated LFS pointer for that ignored stage artifact. The replay verified the accepted publication and digest.
- Determinism PASS: two fresh processes produced identical logical digest `38f75c590d1c4912c89b952a452fae2a3da2192988d7493893c7e081ada79126`.

## Remaining live capability and next stage

- Live BaoStock strict binding remains `BLOCKED_DEGRADED / OPEN_AUDIT` under `V4-06-BAOSTOCK-BINDING-TOLERANCE-01`. No tolerance or denominator semantics were inferred, and endpoint success is not treated as binding acceptance.
- The `DEGRADED` candidate state refers only to unavailable live BaoStock strict-binding capability; the R2 algorithm and persistence contract gates passed.
- Next stage: independent external audit of this R2 candidate. Do not create an Accepted Head before that audit.

## Evidence files

- `V4_06_R2_STAGE_ENTRY.md`
- `V4_06_R2_CONTRACT_SEMANTICS_ACCEPTANCE.json`
- `V4_06_R2_TOLERANCE_SCHEMA_ACCEPTANCE.json`
- `V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json`
- `V4_06_R2_CORE_ISOLATION_ACCEPTANCE.json`
- `V4_06_R2_RUNTIME_TEST_RECEIPT.json`
- `V4_06_R2_CLEAN_CHECKOUT_RECEIPT.json`
- `V4_06_R2_DETERMINISM.json`
- `V4_06_R2_STAGE_CANDIDATE_MANIFEST.json`
