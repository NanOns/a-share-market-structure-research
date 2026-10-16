# V4 production data dependency migration design R1

- Contract: `V4-REPOSITORY-GOVERNANCE-RESET-20261015/R3` (scope update 2026-10-16)
- Design state: `PARTIAL / NOT_EXECUTABLE`
- Inventory date: 2026-10-16 (Asia/Shanghai)
- Database: existing `127.0.0.1:5432/market_research`; catalog queries ran in read-only transactions
- Production runtime at inventory: `NOT_RUNNING`; ports 28765 and 28766 had no listener
- Read connection: V4 reader role, then explicit V4 DSN, then the existing `WORKBENCH_PG_DSN`; write connections still require explicit `V4_NATIVE_PG_DSN`

This is a field-level migration design, not evidence that data was migrated or accepted. It does not authorize DDL, PG writes, Head movement, service startup, source-file cleanup, or production cutover.

The V4 read connector now reuses the project's existing Workbench DSN only through the `read_only=True` connection path when no V4-specific DSN is configured. The writer connector remains fail-closed and still requires its explicit V4 DSN. No DSN value was added to code or documentation.

## Current identity and acceptance facts

Two ignored local Head JSON files exist under `data/v4/`:

| File contract | Date and flags recorded by the file | Boundary |
|---|---|---|
| `V4_DATA_ACCEPTED_HEAD_V2` | `accepted_trade_date=2026-09-30`; `AS_RECORDED=false`; `knowledge_lineage=RECONSTRUCTED_CORRECTED`; file records `EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN` | Historical Head descriptor with nine component artifact references. The descriptor's status is not a current running-service observation and is not copied into PG acceptance without source-level verification. |
| `V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1` | `accepted_trade_date=2026-10-09`; authority `USER_AUTHORIZED_READ_ONLY_DAILY_V1`; `AS_RECORDED=false`; `PIT_ELIGIBLE=false`; historical PIT permission false; scope `DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY` | Research/reprojection authority with 88 nested file references (58 `.gz`, 25 `.json`, 5 `.jsonl`). It is not a production eligible Head. |

Neither file was modified. Their referenced payloads were not opened during this catalog check. Source roots remain read-only. The earlier WP-0 statement that no current production process was running remains true; the earlier statement that there was no local Head file is corrected by this inventory.

## Existing PostgreSQL structures

The canonical `v4` schema has the structures below. On the inventory date, `publications`, `publication_heads`, `state_heads`, `source_packages`, `publication_consumed_sources`, `security_membership_facts`, `universe_snapshots`, and `universe_members` each had zero rows. `source_revisions` had 40,455 rows, `provider_lifecycle_fact_history` 17,962, `security_lifecycle_history` 6,440, and `security_membership_interval_history` 16,053. Counts alone do not establish acceptance or PIT eligibility.

| Responsibility | Existing relation and useful columns | Current gap / mapping rule |
|---|---|---|
| Accepted publication and current pointer | `v4.publications`: `publication_id`, `trade_date`, `revision_no`, `status`, `model_namespace_id`, `core_revision`, `source_manifest_sha256`, `computation_identity_sha256`, prior-session identity, calendar, and `accepted_at`; `v4.publication_heads`: date/namespace/publication/state identity; `v4.state_heads`: namespace/state/publication/logical digest | All three relations are empty. Preserve the allowed status and prior-state checks. Do not turn a file flag into `ACCEPTED`; publish only after full owner/source/quality consistency checks and a transactional pointer update. |
| Source identity and provenance | `v4.source_packages`: contract/version, package SHA, page and observed time, declared/target dates, parser version, manifest, accepted scope; `v4.publication_consumed_sources`: publication/source key/revision/digest; `v4.source_revisions`: logical fact/revision, payload/digest, effective interval, provider/observed/ingested/system times, supersession, tombstone | Package and consumption relations are empty. Existing source revisions are not implicitly linked to any of the 88 file references. Match by verified content SHA and source contract; never infer source time or identity from a path. |
| Security identity/lifecycle | `v4.security_lifecycle_history`: security ID/symbol/type, board and dates, status/quality, source contract/revision/identity and availability clocks; `v4.security_membership_interval_history`: normalized interval/boundary basis, provider and roster dates, quality, evidence, source revision/identity and clocks | Existing history rows have not been proven to be the exact Head inputs. Preserve each source revision and boundary quality; do not promote reconstructed membership to point-in-time truth. |
| Dated universe | `v4.universe_snapshots`: contract/version, trade date, observed/ingested/system times, basis, logical digest and member count; `v4.universe_members`: snapshot/security/type/source revision/quality | Both relations are empty. Use only when each member set and its source/clock can be verified; keep `PIT_OBSERVED`, reconstructed, and diagnostic bases distinct. |
| Immutable domain Owner | Seven hash-named `v4_*` namespaces contain sealed Owner versions: three `V4_RESEARCH_PRIORITY_PG_OWNER_R1` versions with declared counts 5,625/5,625/5,626; three `V4_OPERATIONAL_RISK_PG_OWNER_R1` versions with 3 rows each; one `V4_SECTOR_LIFECYCLE_PG_OWNER_R1` version with 400 rows. Owner versions carry token/T0/contract/digest/count/database identity/sealed state; payload tables carry JSONB and SHA. | These are real existing PG Owner objects, not empty namespace candidates. Their payloads were not read. Their constraints bind payload to Owner version, but no FK binds them to canonical `v4.publications`; the current canonical Head has no mapping to them. Preserve them pending token/schema/consumer identity mapping. Do not add a second Owner store by default. |

Other hash-named `v4_research_*`, `v4_history_*`, `v4_forward_*`, and `v4_jobs_*` relations exist. Their namespace hash does not prove they are current, accepted, production-owned, or safe to delete. The code-derived namespaces absent from WP-0 remain absent; they do not describe every namespace in the database.

## Dependency mapping to complete before executable DDL

| Existing caller/input | Fields actually needed by the caller | Candidate PostgreSQL source/target | Owner, identity and time rules | Unresolved evidence / validation |
|---|---|---|---|---|
| `operational_daily_owner_v1.py` reads `V4_OPERATIONAL_RESEARCH_HEAD` and per-date owners | target/previous session; revision scope; accepted state; lifecycle/identity; membership binding; source digests; producer and rule bindings | `publications`/`publication_heads`/`state_heads`; source and membership relations; existing Owner relations where proven. A minimal publication-to-owner binding may be needed if current composite keys cannot express the association. | Preserve the Head file SHA and each referenced owner/source SHA as migration identity; preserve `AS_RECORDED=false`, `PIT_ELIGIBLE=false`, and read-only scope. No status promotion. | Resolve all consumers and each file binding; verify each referenced file, size and SHA; compare exact row counts/digests; map 2026-10-08/09 inputs; test missing-file behavior and retry. |
| `r43_owner_replay.py`, `r43_structure_replay.py` read acquisition, capture, Core replay, member snapshot and typed delta | source key/package SHA, provider/observed/ingested clocks, effective dates, entity identity, membership intervals, quality and predecessor relation | `source_packages`, `source_revisions`, `publication_consumed_sources`, lifecycle/membership history and the existing immutable Owner stores | Preserve source revision identity and `supersedes` edges. File and Git SHA are not substitutes for source-content SHA. | Inspect call graph and exact fields without accepting old receipts as business authority; establish which current Owner schema/token each caller reads. |
| `operational_runtime_acceptance_r1_1.py` checks producer/source SHA bindings | original accepted producer SHA, new execution SHA, input digest, admission decision | Existing `publications.computation_identity_sha256` and a versioned admission relation only if its fields cannot represent the required distinction | Keep original producer identity immutable; candidate source changes do not inherit prior acceptance. | Specify migration compatibility and prove no acceptance bypass; test 13/14/15 legal relation and unchanged qualification. |
| Research snapshot reader and current service | immutable snapshot/domain rows, snapshot digest, release/T0, source and quality metadata | Existing `v4_research_*` snapshot schemas plus `snapshot_identity`; a PG Head/authority binding must be verified from consumer code | One read transaction per request; verify database identity and logical digest; do not use descriptor files as the sole authority for business state. | Enumerate exact live consumers and matching descriptors; current runtime is stopped and its configured root/package is absent. |
| BaoStock request ledger and source acquisition | bounded provider call facts, package/source binding and clocks | Source package/revision and job/source-probe relations; operational logs only for non-authoritative diagnostics | Credentials excluded; M14 hotlist remains request-scoped and is not persisted | Map each caller and retention need; do not persist M14 raw response, rows, batches, or historical snapshots. |

## Design constraints and write gate

1. Reuse existing `v4` publication/source/history structures and existing immutable Owner schemas where their owner/token and content identity are verified. Do not create a generic duplicate registry before the missing publication-to-owner relationship is demonstrated.
2. If an association table is needed, first prove the minimal key and FK design against the existing publication keys, domain names, Owner schema/token/T0, immutable digest, producer/input digest, quality, and clocks. A schema name string cannot provide a normal cross-schema FK to dynamically hashed Owner tables; the loader must verify the referenced immutable version and database identity in the same accepted-read boundary.
3. `source_packages` and `publication_consumed_sources` are currently empty; define how package facts become a revision and how a publication records consumed source revisions before writing any rows.
4. Draft executable SQL must include unique/FK constraints, indexes, roles, parameters, bounded row counts, readonly preflight, idempotent rerun, conflicting-SHA rejection, transaction boundary, before/after checks, and rollback semantics. It must not move a Head during import.
5. A write request must state the exact schema/tables, expected rows, whether writes are append-only, the affected data and consumers, transaction/rollback plan, privilege source, and post-write cleanup responsibility. All writes use the existing `market_research` instance; no new DB or port.
6. Keep `M14` approved-source contracts and its non-persistence hotlist exception. No change to the TDX source root or to existing accepted data during this design stage.

## State and next step

WP-2 is `DESIGN_IN_PROGRESS / NO_WRITE_AUTHORIZATION`. Catalog metadata confirms that suitable PG components already exist but are not linked to the file Heads, and that several immutable Owner namespaces are populated. The exact old-field-to-row mapping, current Owner binding, 2026-10-13/14/15 input relationships, and minimum association design remain unverified. Next: finish caller/descriptor mapping and readonly consistency checks, then present an executable migration plan with exact target tables and rollback; only after a specific write scope is approved may WP-2 apply it. No migration SQL has been executed.
