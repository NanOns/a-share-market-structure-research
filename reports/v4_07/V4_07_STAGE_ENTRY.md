# V4-07 Stage Entry — Stock Base Seed R1

- Stage contract: `V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929` §12–32 (Workstream B)
- Starting HEAD: `0f13e1b55d86ee74dfc489a48e95a766111a617a`
- Dependency Commit A: `4c6051586a617d01f2ebbe142ea4ded05660fec7` (`fix(v4-06): align turnover context with REV2`); V4-07 work is based on A and touches no V4-06 files.
- Authority: `AGENTS.md`; REV2 `DA-MSR-V4.2.2-CODEX-REV2` §§14.2–14.4, 78, 87A (and §10E for delta3 definition); `data/v4/V4_05_ACCEPTED_HEAD.json`; `data/v4/V4_STAGE_ACCEPTED_HEAD.json`; accepted V4-05 R4.2 bindings.
- Stage boundary: candidate-only V4-07 from accepted V4-05 Core. No V4-06 input, accepted-head promotion, or V4-08 work.
- Target: `2026-09-28`; formal publication `PUB-3c03e227-c60a-4d8c-86ae-2861507c257b` (Core Profile row namespace `V4_05_R4_T0_CURRENT_COORDINATE`); accepted Core logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`; row scope 5,222 identities.
- Accepted profile artifact: `reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz`, SHA-256 `9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`.
- Accepted factor artifact used for `rps5_delta3`: `reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz`, SHA-256 `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`, logical digest `0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2`.
- Accepted row accounting observed before implementation: SH_MAIN 1,702; SZ_MAIN 1,494; CHINEXT 1,408; STAR 618. Both files contain 5,222 unique identities for the target date.
- Input finding: the accepted `rps5_delta3` field is UNKNOWN on all 5,222 rows with `BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY`; V4-07 will preserve this accepted UNKNOWN. The Core Profile has no accepted `close[t-1]` or `MA20[t-1]` field; MA20 reclaim therefore remains UNKNOWN when that OR branch is needed. No raw-source recomputation is authorized by this stage contract.
- Persistence allocation: migration `015` and isolated rollback path `src/workbench_db/migrations/v4_postgres/rollback/015_v4_07_base_seed_results.sql`, following parallel Workstream A's migration `014` claim.
- Contract freeze: `config/v4_07_base_seed_contract_v1.json`, `config/v4_07_parameter_set_v1.json`, `config/v4_07_field_registry_v1.json`, `config/v4_07_machine_vectors_v1.json`. Production detector work starts only after a successful freeze receipt.
- Evidence path: `reports/v4_07/`. Acceptance remains `PENDING`; next stage after candidate closure is independent external V4-07 review. V4-08 remains blocked.

- Contract freeze result: `PASS_CONTRACT_FREEZE_CANDIDATE`; receipt `reports/v4_07/V4_07_CONTRACT_FREEZE_RECEIPT.json`; 30 formula vectors independently evaluated before detector code.
- Persistence contract frozen before migration: `config/v4_07_persistence_contract_v1.json`; migration slot `015` (Workstream A owns `014`).
- Current acceptance result: contract/persistence contracts frozen; candidate implementation and runtime gates pending.
- Stage-entry result: scope, accepted source bindings, BASE_SEED_V1 contract, field registry, vectors, and persistence contract are recorded before detector implementation. Candidate execution and release gates remain pending at stage entry.

## Candidate closure

- Workstream A dependency commit: `4c6051586a617d01f2ebbe142ea4ded05660fec7`.
- Candidate implementation commit: `8cf4b5b87596ef128d47586711549a9ab7cd6dc9`.
- Full market result: 5,222 rows; `FALSE=2,443`, `UNKNOWN=2,779`, `TRUE=0`; logical digest `b2fba6054f93d5155198982cda10feab8a21c4239e94df7023b7dbca2b654cd1`.
- Contract vectors, A–E isolation matrix, deterministic replay, independent 5,222-row recompute, isolated migration/rollback, and the required combined regression all PASS.
- Combined regression output: `533 passed, 2 skipped in 28.21s` on disposable PostgreSQL 18.6 database `market_research`; the temporary cluster was removed. `WORKBENCH_PG_DSN` was passed in process environment; `config/.env` was neither read nor created.
- Accepted V4-05 `rps5_delta3` is UNKNOWN on every row due to `BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY`; accepted T-1 close/MA20 fields are absent. Those UNKNOWNs are preserved without raw-source reconstruction.
- Terminal status: `V4_07_BASE_SEED_CANDIDATE_R1`; no accepted-head promotion. Await independent external V4-07 audit before any subsequent stage.
- Evidence index: `reports/v4_07/V4_07_STAGE_RESULT.json` and `reports/v4_07/V4_07_STAGE_CANDIDATE_MANIFEST.json`.
