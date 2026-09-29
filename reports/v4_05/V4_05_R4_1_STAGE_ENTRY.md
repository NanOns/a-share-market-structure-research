# V4-05 R4.1 Stage Entry

## Contract and scope

- Stage contract: `V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE`.
- Governing task: `docs/evidence/V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE_TASK_20260929.md`.
- Latest prior audit: `docs/evidence/V4_05_REPLAY_GATE_A_R4_EXTERNAL_AUDIT_20260929.md`.
- Starting HEAD: `e751c9dc63ba6e6325b50daa15e849091e18f5dc`.
- Implementation and source-input commit: `bdc2f65a09efc006fe9ca5806f3d5b244b564f42`.
- Scope is limited to closing PostgreSQL ledger replay (B03) and governance hash-domain / clean-clone determinism (B05).

## Frozen R4 values

- Target date: `2026-09-28`; target identities: 5222.
- 1/3/5-session market reference returns: `-0.022314506957301243`, `-0.03792535346523633`, `-0.01769091161662751`.
- Period rows: 694692; full-scope factor rows: 5222; core-profile rows: 5222.
- Market regime trend axis remains `UNKNOWN`.
- R4→R4.1 business-field changes: 0; state changes: 0.

## Stage evidence and acceptance

- PostgreSQL: psql (PostgreSQL) 18.6; 12 official migrations; I01–I05 pass in an isolated disposable database; production connection used: `false`.
- Hash policy: `PASS`; the original Accepted Head promotion binding is preserved while downstream JSON identities use `CANONICAL_JSON_SHA256_V1`.
- Exact pushed-commit clone: `PASS`; 7 LFS source inputs restored, 10 generated outputs compared byte-for-byte.
- Published R4.1 LFS payload restore: `PENDING_ARTIFACT_PUSH`.
- Runtime suite: `426 passed, 2 skipped in 4.33s`; PostgreSQL schema test ran; both skipped tests and reasons are listed in the runtime receipt.
- R4.1 status: `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_1`. External acceptance remains `PENDING`; no V4-05 Accepted Head was created and no V4-06/V4-07 stage was started.
- Next stage: `INDEPENDENT_EXTERNAL_AUDIT_R4_1`.

## Evidence files

The full file hash inventory is in `reports/v4_05/V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json`; independent checks are in `reports/v4_05/V4_05_R4_1_INDEPENDENT_POSTCHECK.json`.
