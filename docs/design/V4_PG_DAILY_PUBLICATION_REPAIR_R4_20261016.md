# V4 PG 日发布 R4 现役数据链修复

- Contract: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R4`
- Audit baseline: `4fa5dd2bc8f4cf28668a66d65dd1095c61687c6e`
- Branch / PR / Issue: `codex/v4-workspace-cleanup` / #3 / #2
- Upgrade basis: R3 daily-publication repair and its acceptance report; R2 repair for final migrations 003–010; R8 unified-source contract; V4 runtime performance repair; production-data migration design; daily operations and rollback contract.
- Scope: complete manifest codec use from producer helper through candidate and reader; read/parse page facts with exact publication/source bindings; implement the minimum candidate-readiness plan.
- Boundary: all writes remain plans only. No PG DDL/DML, accepted Head change, server start, 28765 deployment, history rewrite, or physical deletion.

## Source manifest: producer → candidate → reader

`v4.publication_consumed_sources` supplies `source_key`, `source_revision_id`, and its recorded digest. The joined `v4.source_revisions` row supplies `logical_fact_id`, `revision_no`, `digest`, `effective_from`, `effective_to`, `provider_available_at`, `observed_at`, `ingested_at`, `system_available_at`, and `tombstone`. The consumed-source digest must equal the revision digest. The codec also requires unique source keys, positive integer revisions, ISO dates, aware timestamps, the established UTC six-digit timestamp form, and typed tombstone flags. Candidate checks nonempty complete rows, all source bindings, digest equality, T0 window, tombstone, mandatory clocks, and `system_available_at >= max(observed_at, ingested_at)`. Reader uses the same codec to rehash rows read from the exact publication's consumed-source set and keeps its existing acceptance-time clock checks.

`build_source_manifest()` is the producer entry point. `build_publication_candidate()` calls it, stores the computed SHA, and rejects a mismatching optional caller SHA; the candidate cannot be made valid by supplying a digest alone. The reader rejects missing/unknown contract markers and mismatches. Golden-vector tests exercise order, UTC normalization, nulls, clock/type validation and mutation.

Schema evidence has a remaining source-producer gap: `source_packages.accepted_scope` is not connected by a foreign key or another migration-defined relation to `source_revisions`, and this checkout has no verified current writer that populates the canonical publication consumed-source set from daily producer output. Thus the field mapping above is exact for persisted source revisions, but package authority and a real production producer sample remain unverified. No source package authority or live T0 status is inferred from a path or timestamp.

## Current page data map

| Page | Exact existing PG source | Parsed business fields | State / gap |
|---|---|---|---|
| Summary | `v4.event_observations`, filtered by exact `publication_id` and ACTIVE status | `payload.effective_event`, `primary_scenario`, `counterevidence`, `trade_date`, `why_now`; missing fields returned per event | Direct event rows can be shown. Replay and identity names remain uncovered; operational risk is a separate supplement. |
| Entity | `v4.security_lifecycle_facts` restricted to source revision IDs consumed by this publication and effective at its T0 | security id/type, board, listing dates, ST/trading state, effective dates, quality, source revision | Lifecycle only. No publication-bound daily OHLCV, state projection, or identity-name relation exists in the final V4 migration set. |
| Radar | Existing `research_priority` hashed Owner through the publication module binding | `stocks.all_items`, `sectors.all_items`, `rule`; only exact present consumer keys are projected | Priority supplement only; formal radar ledger, replay and names remain uncovered. |
| Sector | Existing `sector_lifecycle` Owner through the publication module binding | sector id, maturity, health, T0, contract | Lifecycle supplement only. `sector_membership_facts` is not bound to the selected publication source set. |
| Cohort | No verified publication-bound relation in current V4 migrations | None | PENDING with a specific missing-relation reason. |
| Settlement | No verified publication-bound relation in current V4 migrations | None | PENDING with a specific missing-relation reason. |
| Health | operational-risk and sector-lifecycle Owner supplements | Exact existing status/change and health/maturity paths | DEGRADED; replay and maturity completeness are unavailable. |

`PgPublicationReader` reads these direct facts in the selected publication snapshot. `PgV4CurrentAdapter` returns `parsed_business_fields`, exact field-path mappings, and per-group gaps. It never aliases missing values or returns `READY_CURRENT_ACCEPTED`; the default artifact reader remains in place and the PG adapter remains opt-in.

## Minimum daily publication plan

`V4_DAILY_PUBLICATION_MINIMUM_R1` defines a pure candidate-planning floor: publication/date/namespace/revision identity; one observed PG database identity; valid computation and state-head digests; a nonempty complete source manifest under the supported version; matching source rows/bindings; valid T0, tombstone, digest, and clock rules; and all explicitly required Owner families. The currently proven Owner contracts mark all three existing families capability-optional, so no empty or fabricated Owner is required for the daily base. Supplied optional Owner results still must pass their fixed contracts and match the candidate database identity.

On passing these checks the planner emits `CANDIDATE_READY`, `publish_status=CANDIDATE`, and `head_update=PLAN_ONLY_NOT_EXECUTED`. `plan_publication_head_change()` accepts only this versioned minimum contract and returns an exact insert-if-absent/CAS description. Neither status grants persistence: PG readback, accepted-row transaction, Head write and post-commit readback remain separately gated. Page-level readiness stays degraded/pending wherever required data is absent.

## Acceptance record and next stage

- Code and deterministic focused tests: see `reports/stage/V4_PG_DAILY_PUBLICATION_COMPREHENSIVE_TEST_REPORT_20261016_R4.md`.
- Live PG catalog / Owner / Head: `DB_READ_ENV_UNAVAILABLE`; no DSN found, no connection attempted.
- SQL transaction / trigger / concurrent CAS: not run; no isolated writable PG environment was established or authorized.
- Full page parity and live source-producer-to-publication evidence: not achieved.
- Production and 28765: unchanged.
- Next: provide approved read-only PG configuration and source package/revision producer binding evidence; then audit real page parity. DDL/CAS requires an authorized isolated PG environment. Keep research-snapshot divergence and governance-scope review separate.
