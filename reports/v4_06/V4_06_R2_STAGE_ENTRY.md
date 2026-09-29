# V4-06 R2 Stage Entry

## Stage contract

- Stage: V4-06 Supplemental Enrichment, R2 contract-semantics repair.
- Authority: project `AGENTS.md`; REV2 §§9.6, 10H, 10I, 78, 87A; accepted V4-05 and global accepted-stage heads; `V4_06_R1_INDEPENDENT_EXTERNAL_AUDIT_20260929.md`; R2 stage task dated 2026-09-29.
- Required starting HEAD: `0f13e1b55d86ee74dfc489a48e95a766111a617a` (verified).
- Accepted input: publication `PUB-3c03e227-c60a-4d8c-86ae-2861507c257b`, date `2026-09-28`, Core logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`, 5222 identities.
- Prior external result: `V4_06_EXTERNAL_ACCEPTANCE_BLOCKED_R1_CONTRACT_SEMANTICS_REPAIR_REQUIRED`; the R1 implementation and evidence remain immutable historical evidence.

## Frozen R2 engineering contract

1. Percentiles `turnover_pct5/20/60` use the REV2 empirical midpoint formula multiplied by 100 and have range `[0,100]`.
2. Canonical `turnover_state` uses `turnover_pct60` and REV2 thresholds `<20 LOW`, `<70 NORMAL`, `<90 ELEVATED`, `<97 HIGH`, else `EXTREME`; the 20/70/90/97 boundaries are exact.
3. `binding_quality` records provider/source binding. Semantic state and capability state are separate. The versioned reason-state map defines `PENDING`, `UNAVAILABLE`, and `UNKNOWN_DATA`.
4. `turnover_context` is deprecated/internal and, whenever semantic classification is available, is an exact alias of canonical `turnover_state`.
5. Migration 014 and rollback amend only V4-06 sidecar percentile constraints. Migration 013 is immutable; no Core table or accepted V4-05 row is changed.
6. The runtime consumes the real persisted tolerance schema and strict binding remains disabled unless every accepted contract, source, dataset, denominator, reviewer, timestamp, evidence, and tolerance gate passes. Current real config therefore remains fail-closed.
7. `supplemental_extension_note` is a versioned annotation over accepted Core extension facts and supplemental-source state; it cannot affect Core, PREWATCH, Base Seed eligibility, maturity, or Focus.

## Evidence and entry result

- Evidence inspected: external R1 audit; REV2 source clauses; current persisted tolerance config; R1 engine, tests and migrations; accepted V4-05 head/digest.
- Entry acceptance: `PASS`; the R1 S01-S03 contract-semantic blockers were repaired and the required semantic, binding, persistence, isolation, determinism, and clean-checkout gates passed.
- Implementation commit: `4c6051586a617d01f2ebbe142ea4ded05660fec7` (`fix(v4-06): align turnover context with REV2`).
- Focused runtime: 69 passed; isolated PostgreSQL 18.6 migration 014 and rollback passed; migration checksum `fff140f483738b6fb8e94e06a4e2c681111de94ceb1c415d18c188a9d95977e3`.
- Accepted V4-05 Core publication/digest were unchanged by the isolated persistence probe. A clean detached checkout of the implementation commit passed the focused suite and isolated migration replay using the materialized accepted V4-05 input root read-only.
- Candidate result: `V4_06_DEGRADED_PASS_CANDIDATE_R2`. This is an engineering candidate only; it does not create an Accepted Head or claim external acceptance.
- Cross-cutting audit `V4-06-BAOSTOCK-BINDING-TOLERANCE-01` remains OPEN. No tolerance or denominator semantics will be inferred.
- Next stage: independent external audit of the R2 candidate; no Accepted Head promotion in this task.
