# V4 PG-only 日发布候选读取与发布链设计 R1

- Contract: `V4-PG-DAILY-PUBLICATION-CANDIDATE-20261016/R1`
- Scope: current V4 readers and publication metadata only.
- Candidate implementation: `src/workbench_db/v4_publication_reader.py`, `src/workbench_db/v4_publication_candidate.py`.
- SQL proposal: `docs/design/sql/V4_PUBLICATION_MODULE_RESULTS_CANDIDATE_R1.sql`.
- Status: `CODE_CANDIDATE / PG_LIVE_PENDING / PRODUCTION_UNCHANGED`.
- No database DDL/DML, Head change, service startup, production switch, source-file deletion, or historical rewrite has been performed.

## 1. Current V4 entry and data-path map

| Entry | Consumer | Data path | Identity / requiredness | Current candidate relation |
|---|---|---|---|---|
| `/api/v4/current/context` | `v4_control_server_v2.Handler` → `CurrentAcceptedV4Reader.read('context')` | `READS_ARTIFACT` (authority and Head JSON); validates runtime authority before responding | Current accepted read contract and context token; not an accepted PG publication | `v4.publications`, `publication_heads`, `state_heads` are candidate only; exact mapping absent |
| `/api/v4/current/summary` | same handler → `.read('summary')` | `READS_ARTIFACT` (events, observations, identity names, replay) | event effective date and event quality; no module requiredness inferred by the new code | `event_observations` is a candidate relation; acceptance link needs exact event revision |
| `/api/v4/current/radar` | same handler → `.read('radar')` | `READS_ARTIFACT` (radar publication/ledger, replay, identity names) | validates trade date, publication ID and evidence class; upstream capability is degraded | existing research-priority Owners exist, but publication binding is not established |
| `/api/v4/current/entity` | same handler → `.read('entity')` | `READS_ARTIFACT` (raw daily, identity, states/state projection, events) | projection source SHA must equal state binding; per-field UNKNOWN/DEGRADED preserved | lifecycle/source revision relations and domain Owner tables are candidates; exact common publication binding absent |
| `/api/v4/current/sector` | same handler → `.read('sector')` | `READS_ARTIFACT` (membership JSONL) | `FORWARD_PIT_MEMBERSHIP_ONLY`; algorithm state remains UNKNOWN | membership history/facts candidates; existing canonical membership facts/snapshots were empty in last recorded inventory |
| `/api/v4/current/cohort` | same handler → `.read('cohort')` | `READS_ARTIFACT` (cohort and maturity evidence) | T0/evidence class checked; maturity remains PENDING absent evidence | FEP/forward relations only if enrollment and Owner identity match; latest relevant audit says `fep` had no tables |
| `/api/v4/current/settlement` | same handler → `.read('settlement')` | `READS_ARTIFACT` (outcome and settlement receipts) | outcome revision/date retained; maturity remains PENDING | settlement/outcome candidate relations unresolved |
| `/api/v4/current/health` | same handler → `.read('health')` | `READS_ARTIFACT` (data Head, component rows, replay, maturity) | checks component count and date; permission does not grant write capability | publication/source-package/source-revision relations are candidates; current canonical Head absent in last recorded inventory |
| six formal pages | UI assets call `/api/v4/current/*` and `/api/v4/*` through the service | candidate context shared only when explicitly injected; production routes remain unchanged | context token prevents stale page requests on the existing reader | PG candidate reader is not wired into default production service construction |
| current PG Owner BFF routes | `CoreProductBFFR1` / PG domain loaders | `READS_PG` for immutable priority/risk/sector Owners, but local Authority JSON binds the loaders | Owner token/T0/contract/digest/row-count and database identity required | existing sealed Owner namespaces are candidates; missing authority files and no canonical publication relation prevent full current-page binding |

This mapping covers the current read entry points. R1's prior audit noted 42 report/evidence hits. A plain literal search on this checkout matched 77 Python files because it also catches report output paths, comments and historical modules; that count is not a count of live readers. Only the current reader and producer/BFF paths named by the call graph are treated as active here. Other matches remain `UNKNOWN` until their callers are shown reachable from an active V4 entry.

Requiredness is intentionally not guessed. `config/v4_current_accepted_read_contract_v1.json` names the data groups each existing module reads; it does not, by itself, state whether every page module must block publication. The candidate API requires the caller to pass an effective V4 requiredness mapping and fails with `MODULE_REQUIREDNESS_UNKNOWN` otherwise.

## 2. Reuse findings and minimal association proposal

Migration `001_v4_phase0_foundation.sql` proves that `v4.publications` is keyed by `(publication_id, revision)` and has status/date/model namespace/source manifest/computation identity; `v4.publication_heads` points to that exact revision; `v4.publication_consumed_sources` binds source keys/revisions/digests. The source table is append-only. `publication_consumed_sources` represents sources, not module Owner results.

The existing hashed Owner schemas are independently immutable and carry Owner identity, but their dynamic schema/table names cannot receive ordinary foreign keys from `v4.publications`. Existing canonical publication rows have no general module-result association column or relation. Consequently this branch proposes at most one identity-only association relation, `v4.publication_module_results`, with a composite FK to the existing publication key and unique `(publication_id, revision, module_key)`. It stores no payload and creates no new Head or state machine. This is a code/design candidate, not an approved or executed DDL.

The SQL trigger verifies same-database name and relation existence. Reader code compares the existing project database identity tuple (`database`, `database_oid`, `host`, `port`) and calls only fixed, per-module resolvers; it never turns `owner_schema` or `owner_relation` from a row into dynamic SQL. Each resolver must return and match token, contract, T0, digest, row count and database identity in the same read-only transaction.

## 3. Candidate reader behavior

`PgPublicationReader` is opt-in and isolated from `CurrentAcceptedV4Reader`:

1. Requires caller-selected trade date and model namespace; it never picks “latest”.
2. Opens one `REPEATABLE READ READ ONLY` transaction with bounded timeouts.
3. Selects one exact accepted Head and returns `NO_ACCEPTED_PUBLICATION` when absent.
4. Verifies the configured project database identity before reading module bindings.
5. Requires an explicit module requiredness map; required unbound rows fail with `MODULE_RESULT_UNBOUND`.
6. Preserves owner quality, `as_recorded` and PIT values. It never upgrades them.
7. Payload resolvers are injected and must verify the binding identity in the same transaction. Missing required resolver fails closed.
8. The context token covers the selected publication and sorted module binding digest; later page/module requests can provide both expected identity and token, and stale bindings fail with `STALE_CONTEXT_REQUIRES_REFRESH`.
9. It imports no filesystem reader and has no artifact/SQLite fallback.

The default V4 server continues constructing `CurrentAcceptedV4Reader`; no default route or port now instantiates the candidate. A later preview may explicitly inject it into a 28766-only handler after its actual PG bindings exist. No service was started in this task.

## 4. Producer → candidate → acceptance code boundary

`build_publication_candidate` is a pure planner. It compares the producer-observed source revision/digest map with the expected source manifest, then checks publication/computation identities, module keys, explicit requiredness, owner locators, token/contract, row count, result digest and quality flags. A source revision or digest mismatch fails with `SOURCE_IDENTITY_MISMATCH`. It emits only `publish_status=CANDIDATE`, `accepted_at=NULL`, and `head_update=NOT_AUTHORIZED_BY_PLAN`. Missing required modules or UNKNOWN requiredness produce `CANDIDATE_INCOMPLETE`.

Canonical `v4.publications` is append-only, so candidate creation must not insert a row as CANDIDATE and later update it to ACCEPTED. A future, separately authorized acceptance transaction must pre-verify exact results, insert the accepted publication and immutable source/module associations, CAS the date/namespace Head against its exact prior identity (including initial Head absence), append an event, then read back after commit. This contract is documented in the SQL proposal only; no PG writer or acceptance SQL was executed.

The last recorded database inspection found no canonical accepted Head. Do not convert local JSON `PASS` values or historical artifacts into accepted PG rows. Real source admission, producer outputs, and first-publication initial-boundary semantics remain `PG_LIVE_PENDING`.

## 5. Scope exclusions

- Research snapshot SQLite/PG release equivalence remains a separate unresolved data migration; this reader does not use that snapshot.
- Old Owner source recovery is required only for a source/Owner chosen for a real publication, not as a project-wide blocker.
- No M14, V4-before code cleanup, algorithm changes, user data changes, service startup, real DDL/DML, Head change, production schedule, 28765 switch, physical file deletion, or Git history rewrite.
