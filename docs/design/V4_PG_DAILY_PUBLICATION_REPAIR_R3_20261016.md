# V4 PG 日发布独立审计定点修复 R3

- Contract: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R3`
- Audit input: Drive `V4_日发布_PR3_R2独立审计与R3修复任务_20261016.md`
- Audit base: `c7e585239b20ef1bb1678adbef721bfb8af99e46`
- Branch / PR / Issue: `codex/v4-workspace-cleanup` / #3 / #2
- Stage scope: replace endpoint-as-Owner assumptions with existing Owner-family mappings; add canonical source-manifest contract and rehash; implement fixed PG payload resolvers; downgrade candidate page status honestly; targeted tests.
- Exclusions: D0/D1 rerun, default handler swap, PG writes/DDL execution, accepted Head change, service startup/deploy, history rewrite, physical deletion.

## Applicable upgrade and migration contract

Read before implementation: `V4_PG_DAILY_PUBLICATION_REPAIR_R2_20261016.md`, `V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`, `V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`, `V4_DAILY_OPERATIONS_AND_ROLLBACK_R1_20261008.md`, and `docs/design/V4_PRODUCTION_DATA_DEPENDENCY_MIGRATION_DESIGN_R1.md`. R8 confirms the risk producer and consumer reuse their existing immutable PG Owner; it does not grant source/head acceptance or require a parallel Owner store.

The reader is based on final migration sequence 001–010. Migrations 003–009 define `publication_id` identity, `revision_no` lineage, state identity and Head guards. New migration 010 adds a source-manifest contract marker. Legacy rows stay NULL and unknown; new inserts must carry `V4_PG_CONSUMED_SOURCE_MANIFEST_R1`. The R3 owner-binding SQL is a draft only and uses the same publication identity. Neither 001 alone nor the older R2 seven-endpoint SQL is the active owner contract.

## Evidence based Owner and page map

The current PG producer code provides three real immutable Owner families, and this repair reuses them instead of making endpoint-shaped Owner storage:

| Owner family | Existing PG producer / relation | Consumer projection known from code | Remaining limit |
|---|---|---|---|
| `research_priority` | `v4_operational_risk_pg_r1.prepare_priority` → hashed schema `owner_versions` + `owner_payloads`; contract `V4_RESEARCH_PRIORITY_PG_OWNER_R1` | `/api/v4/radar/priority`: `stocks.all_items`, `sectors.all_items`, `rule`, rankability counts | Not the same producer as the formal current radar ledger; no accepted-publication association verified. |
| `operational_risk` | `v4_operational_risk_pg_r1.prepare` → `owner_versions` + `owner_payloads`; contract `V4_OPERATIONAL_RISK_PG_OWNER_R1` | Home risk panel: family `status`, `changes[*].change`, `prior_state`, `current_state`; three named risk families | Does not supply the summary event/replay fields or prove global publication requiredness. |
| `sector_lifecycle` | `v4_sector_lifecycle_pg_r1.prepare` → `owner_versions` + `owner_rows`; contract `V4_SECTOR_LIFECYCLE_PG_OWNER_R1` | Sector detail supplements `maturity`, `health`, evidence scope | Not sector membership, member counts or rotation. Existing data is dated 2026-10-13 in the last recorded inventory; live T0 is unknown. |

`v4_publication_contract.py` names seven current page projections and records the actual consumed field names from `CurrentAcceptedV4Reader` plus the available Owner field paths. Summary/radar/sector/health can expose supplemental Owner families, but all remain `DEGRADED` with `NOT_VERIFIABLE_PAGE_PARITY`; entity/cohort/settlement remain `PENDING`. Missing groups are explicit. Current V4 consumers and paths are in `src/workbench_service/current_v4_context.py`; existing PG BFF reads are in `src/workbench_service/core_product_bff_r1.py`. The PG candidate adapter remains opt-in and the default accepted artifact reader is unchanged.

The three present Owner families are **capability-optional**, not global daily publication requirements. No authoritative producer contract in the reviewed code establishes which absent families block a whole-day Head. This R3 contract therefore refuses to infer a seven-Owner barrier or fabricate empty rows. The global publication completeness rule remains open pending the required producer-contract proof.

## Source-manifest serialization

Contract `V4_PG_CONSUMED_SOURCE_MANIFEST_R1` v1.0.0 hashes the canonical UTF-8 JSON array of every consumed source revision row, in ascending UTF-8 `source_key` byte order, with the exact field set in `src/workbench_db/v4_source_manifest.py`. JSON object keys sort lexically; separators are `,` and `:`; Unicode is emitted as UTF-8; dates use `YYYY-MM-DD`; aware timestamps normalize to UTC with six fractional digits and `Z`; booleans/null remain JSON booleans/null; SHA-256 values must already be lowercase hex. A source-key change or any one-field mutation changes the digest. PIT, AS_RECORDED and quality flags remain untouched.

The contract is forward-only. Existing rows without the new contract marker fail closed as `SOURCE_MANIFEST_CONTRACT_UNSUPPORTED`; this repair does not infer their historical serialization. Unit vectors are synthetic and deterministic; no live PG source sample or accepted manifest SHA was available to verify against the producer.

## PG Owner resolvers and page status

Fixed resolver dispatch reads only the three declared family contracts. It checks schema naming, fixed table/relation, same database identity, owner contract/token/T0/sealed state/row count, account write privileges, payload digest and aggregate Owner digest inside the caller's read-only repeatable-read transaction. Page endpoints project those shared family payloads; no endpoint selects a database callable or dynamic relation. Quality, `AS_RECORDED` and PIT remain as stored.

Candidate adapter outputs are only `DEGRADED` or `PENDING`, with `candidate_only=true`, uncovered input groups and `quality_status=NOT_VERIFIABLE_PAGE_PARITY`. It never emits `READY_CURRENT_ACCEPTED`. The adapter is not attached to the current server.

The pure candidate planner now returns `CANDIDATE_REQUIREMENTS_UNVERIFIED` and `BLOCKED_REQUIREMENTS_UNVERIFIED` because global daily Owner requiredness has no producer-contract proof. Head CAS planning rejects that state. It cannot convert the optional capability list into a complete publication claim.

## Acceptance record

- Targeted source-manifest/Owner/reader/adapter/static suite: **43 passed**. This validates code and deterministic fixtures, not live PG parity.
- `PASS_CODE`: not claimed. Source-manifest contract, owner-family mapping, fixed resolvers, candidate state and tests are implemented, but no real accepted PG manifest/Owner payload sample exists here.
- `PASS_CI`: pending Actions for this R3 commit.
- `PASS_PG`: `DB_READ_ENV_UNAVAILABLE` unless a permitted existing read-only DSN is found; no DDL or DML is run in this task.
- `PASS_PAGE`: not achieved; formal field parity lacks immutable PG Owner/read-model evidence for all page groups and no live same-publication readback.
- `PASS_PRODUCTION`: not in scope or authorized.
- Overall expected state: code-only progress; `EXTERNAL_REVIEW_BLOCKED` until open evidence is supplied.

## Next stage

1. Obtain read-only catalog/Owner/Head evidence through existing secure config and verify actual T0, database identity and owner rows.
2. Reconcile field parity and global requiredness against the live V4 producer contracts; add real result families only when their producer/storage identity is proved.
3. Run draft DDL/trigger/concurrent-CAS tests only in an authorized isolated PG environment; keep production Head and 28765 untouched.
4. Keep P1-04 research-snapshot divergence and PR governance-scope review separate from this code-only acceptance.
