# V4 R17 — Owner-to-API/Frontend Data-Lineage Matrix R1

## Identity and runtime boundary

The explicit PG-candidate BFF reads seven `/api/v4/current/{summary,radar,entity,sector,cohort,settlement,health}` routes. Candidate mode requires one `trade_date`, `model_namespace_id`, and context token and passes the same token through all seven requests; the browser rejects a response whose token differs and does not fall back to the file Head. It is opt-in through `source=pg_candidate`. Normal V4 pages remain a separate serving mode.

The V4 workbench shell has six navigation destinations: sectors, stocks, linkage/focus, market, data/operations, plus the separate research-home view. This six-navigation-plus-home product surface is distinct from the seven candidate APIs. The existing `static/v4-workbench.js` renders the seven API sections with per-field states, values, provenance, query/state filters, explicit context, and visible SOURCE_INVALID failures. The source was inspected, but no 28766 service/browser session or Live PG was available; visual/two-viewport/network-retry checks are NOT_RUN.

## Field-level lineage

| API / UI section | Owner producer | PG relation / identity | Candidate projection fields and current source | Uncovered capability / status |
|---|---|---|---|---|
| `summary` / changes view | optional `operational_risk` Owner | `v4.event_observations` filtered by selected publication; accepted publication context supplies T0/namespace | `effective_event`, `primary_scenario`, `counterevidence`, `trade_date`, `why_now`; Owner path `payload.families.*.status` and `changes[*].change` | replay and identity/security names missing; source-bound fields can be partial; Owner root map is unapproved |
| `radar` / priority view | optional `research_priority` Owner via `v4.publication_module_results` hashed payload | Owner result bound to selected publication; not a formal ledger | `entity_id`, `signal_type`, `eligibility_state`, `priority_bucket`, `trade_date`; stock/sector `all_items[*]` and `rule` | formal radar relation/ledger, replay, identity names missing; supplemental priority only |
| `entity` / security view | no current PG Owner family | `v4.security_lifecycle_facts` joined through `publication_consumed_sources.source_revision_id` | `source_security_key`, `close`, `open`, `high`, `low`, `trade_date`, `list_date`, `ma5`, `ma20`, `ma60`, `history_status`, `profile_payload`, `scenario`, `state`, `health`, `maturity`; current relation only supplies lifecycle fields | prices, named identity, MA/Profile, state events and replay are unavailable; lifecycle does not prove a full security page |
| `sector` / sector view | optional `sector_lifecycle` Owner via `v4.publication_module_results` hashed rows | lifecycle result tied to selected publication; membership is not bound by this relation | `sector_id`, `sector_name`, `member_count`, `algorithm_state`; Owner path `payload[*].sector_id/maturity/health` | actual membership and health/rotation input missing; lifecycle is never treated as sector membership |
| `cohort` / cohort view | no current PG Owner family | no publication-bound cohort relation | `entity_id`, `T0`, `cohort_namespace`, `enrollment_id`, `evidence_class` | radar/cohort/maturity/identity-name groups absent; contract currently unknown for rows |
| `settlement` / outcome view | no current PG Owner family | no publication-bound settlement relation | `enrollment_id`, `horizon`, `outcome_status`, `due_date`, `outcome_revision` | outcomes, settlement receipt, maturity absent; contract currently unknown for rows |
| `health` / health view | optional `operational_risk` and `sector_lifecycle` Owners | hashed `owner_payloads` / `owner_rows` via publication module results | `component`, `row_count`, `quality`, `freshness`, `source_quality`, `maturity`; Owner health/status paths | replay and maturity relations missing; owner supplements are not system health/replay proof |

The candidate adapter reports field coverage and provenance row by row. This phase fixes its top-level status to `DEGRADED` when publication-bound page rows exist even when no optional Owner family is configured; `PENDING` is reserved for no verified rows and no owner results. Missing individual fields remain explicit `SOURCE_MISSING`/`CONTRACT_UNKNOWN` and are never filled from another T0 or namespace.

## Data binding and verification

- Source table: `src/workbench_db/v4_publication_contract.py` (`PAGE_PROJECTIONS`, `PAGE_PG_RELATIONS`); BFF: `src/workbench_service/v4_pg_current_adapter.py`; route map: `src/workbench_service/v4_server.py`; UI: `src/workbench_service/static/v4-workbench.js`.
- `config/v4_pg_workspace_owner_authority_r1.json` has zero approved mappings. No project root, namespace, or Owner permission was invented.
- Formal BFF and browser real-data E2E is `E2E_PARTIAL_NO_PG`; no accepted live PG identity/namespace or reader role was available. No production E2E is claimed.
