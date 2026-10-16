# V4 PG 日发布独立审计定点修复 R2

- Contract: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R2`
- Audit input: `V4_PG日发布_PR3_独立外部代码审计与定点修复任务_R1_20261016.md` (Drive ID `1zb5-Zqi8beFW-4653HygMopOegWwbK3x`); downloaded for this run to `G:/codex_tmp`.
- Frozen audit base: `04044506b0a4e0da54a44299c1c6c8a596f7ecf0`.
- Branch/PR/Issue: `codex/v4-workspace-cleanup`, PR #3, Issue #2.
- Existing D0/D1: reused; no repeat inventory.
- PG evidence status: `DB_READ_ENV_UNAVAILABLE`; no `V4_NATIVE_PG_READER_DSN` or `WORKBENCH_PG_DSN` was available in the command environment. No database read, DDL/DML, service start or production switch was attempted.
- Overall repair status: `CODE_REPAIR_PARTIAL / PG_SCHEMA_AND_OWNER_PARITY_UNVERIFIED / PRODUCTION_UNCHANGED`.

## Applicable source and migration contract

This repair follows the R1 audit order and the current upgrade constraints in `V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`, `V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`, `V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`, and `V4_PRODUCTION_DATA_DEPENDENCY_MIGRATION_DESIGN_R1.md`.

Migration 003 renames `publications.revision` to `revision_no`, drops `publication_heads.revision`, and changes publication identity to the single `publication_id`. Migrations 007–009 bind namespace, prior-session publication/state identity, and the Head's `state_head_id` plus `state_logical_digest`. Migration 001 is only the pre-alignment schema and cannot be used as the final reader/DDL model.

## R1 audit disposition

| Item | R2 work | Status / remaining evidence |
|---|---|---|
| P0-01 final publication identity | Reader/Planner use `publication_id` and `revision_no`; DDL uses FK `publication_id` only; parent chain uses `same_day_revision_parent_id`, lineage and sequence. Static migration/schema contract tests added. | Code/static contract PASS. No `pg_catalog` verification or SQL execution; do not claim live schema compatibility. |
| P0-02 immutable module set | Draft SQL adds a shared transaction advisory lock for Owner insertion and Head visibility, required seven-module completeness before Head, post-Head append rejection, UPDATE/DELETE and TRUNCATE guards. | SQL design/static checks PASS. Concurrency/trigger execution remains unverified without an isolated PG cluster. Draft is not applied. |
| P0-03 source/Owner/state snapshot | One repeatable-read read-only transaction validates Head→publication→state_head, same-day parent lineage, consumed source revision/digest, effective T0 window, tombstone and availability clocks, module contract/T0, database identity, and Owner readback. Metadata-only mode is explicitly marked unverified. | Mock/contract tests cover negative cases. Source manifest serialization is not specified by the existing schema, so its declared SHA is not recomputed; context reports `NOT_PROVEN_MANIFEST_SERIALIZATION_UNSPECIFIED`. Historical module input windows remain possible, while each published Owner result must be for publication T0. |
| P0-04 seven PG page payloads | Added versioned fixed endpoint→module mapping and opt-in `PgV4CurrentAdapter`; added a safe fixed-query resolver for the existing V4 sector-lifecycle Owner family. No default server wiring or file fallback was added. | Partial. The sector-lifecycle Owner is supplemental and does not equal sector membership. Six formal page payload resolvers and a real accepted Head are still absent; the adapter deliberately cannot claim the pages are PG-only yet. |
| P1-01 requiredness | Added `V4_CURRENT_PUBLICATION_MODULE_CONTRACT_R2`; all seven current page modules are required for one complete publication set. Field/input groups are mapped to the existing accepted-read contract; quality is preserved and never promoted. Callers cannot inject OPTIONAL overrides. | Code/static contract PASS; actual source/Owner completeness still needs PG readback. |
| P1-02 Owner readback | Payload readback is default. Missing required resolver, payload row-count mismatch, Owner identity mismatch and digest mismatch fail closed. Metadata-only calls return `METADATA_ONLY_UNVERIFIED`. | One existing Owner-family resolver implemented; six module families not yet implemented. |
| P1-03 read-only role | Reader enforces transaction `READ ONLY` and separately checks superuser, RLS bypass, V4 schema CREATE and DML/TRUNCATE privileges; the concrete Owner resolver checks its schema/table write privileges. | Static/mock implementation only. No live role result; cannot claim the configured account is a read-only database role. |
| P1-04 research snapshot difference | No descriptor substitution or snapshot promotion. Existing mismatch remains explicitly outside this code repair. | Open pending real canonical source/Owner evidence or a separately scoped feature limitation decision. |
| P1-05 PR scope | Kept the authorized PR #3 and governance branch. This PR includes earlier governance commits as well as this repair. The Issue/PR update separately records governance and V4 repair acceptance. | Still broader than this feature; no history rewrite or branch surgery performed. Review those scopes separately before merge. |
| P1-06 CI | Added a focused GitHub Actions job for candidate unit tests plus static final-schema/SQL contract tests. | Local targeted suite is recorded in GitHub. CI result for the new commit must be read after push. Three existing artifact SHA-mismatch reader tests remain excluded from the focused baseline and are not production-equivalence evidence. |

## Entry-point behavior

`PgV4CurrentAdapter` maps `/api/v4/current/{summary,radar,entity,sector,cohort,settlement,health}` to the same-named required module and reads every required Owner in one context before returning a page payload. Unknown endpoints and missing PG publication/Owner bindings fail explicitly. It does not load artifact JSON, SQLite, local Authority files, or the default `CurrentAcceptedV4Reader`.

The adapter remains opt-in and is not connected to `v4_control_server_v2.py`; production still uses the current accepted artifact reader. Do not start a candidate server on another port. A later injection must use only the authorized development slot 28766 and must remain read-only against `127.0.0.1:5432/market_research`.

## Tests and acceptance boundary

The focused local command is:

```text
python -m pytest -q -p no:cacheprovider tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py tests/test_v4_pg_publication_contract_static.py
```

Temporary variables and test output are directed to `G:/codex_tmp`. These tests cover final migration semantics, removed-column regressions, publication-id CAS planning, same-day parent identity, source/Owner/state failures, privilege distinction, requiredness, adapter mapping, append sealing source clauses and fixed-query Owner readback. They do not compile or execute PostgreSQL DDL and do not prove real PG role/readback.

Acceptance must stay `EXTERNAL_REVIEW_BLOCKED` until the six current-page Owner payload contracts are proven against canonical PG relations, source manifest serialization and accepted source rows are reconciled, isolated PG schema/trigger/concurrent-CAS tests pass, and live read-only role/catalog/readback evidence exists. No accepted Head, database data, port 28765, Git history, or source file was changed by this repair.

## Next actions

1. Restore an approved read-only connection through the project's existing secure configuration; do not ask for a DSN in chat or log credentials. Record privilege attestation separately from transaction read-only mode.
2. Reconcile the source manifest's canonical serialization contract before claiming full source-set digest validation.
3. Map each of the six formal pages to real immutable PG Owner families and implement fixed resolvers with field/quality parity; keep unresolved modules fail-closed.
4. Run the SQL against an isolated schema/cluster under `G:/codex_tmp/test_temp` only if the available environment supports that isolation; test post-Head insert rejection, required-module omission and concurrent Head CAS. Do not apply it to production.
5. Read the new commit's focused CI result, update Issue #2 and PR #3, and request review there. Production DDL/DML, first accepted Head, 28765 switch, Git history rewrite and physical deletion remain separately unauthorized.
