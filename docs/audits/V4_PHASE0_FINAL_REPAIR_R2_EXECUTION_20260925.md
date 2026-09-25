# V4 Phase 0 Final Repair R2 — Execution Ledger

- Governing repair card: `DA-MSR-V4-PHASE0-FINAL-REAUDIT-R2`
- Repair card SHA-256: `f51e71ec8a3c02a5551bf07f66366856cf146182a76729b549871a680dcd0fe0`
- Highest technical contract: `DA-MSR-V4.2.2-CODEX-REV2`
- REV2 SHA-256: `744b75906d932d6b11e01a1cd90f6a8de219642620dd30fd`
- Input HEAD: `e3b0a1e3029470a12cb2b9f4dd733ca24a4617a9`
- Execution boundary: additive V4 schema migration only; no database reset, no TDX writes/downloads, no V4-01/02, no scanner/factor/Radar/Focus implementation.

## P0-1 / P0-2 — Publication identity and PIT fact schema

- **Stage contract:** R2 §§3–4 and REV2 publication opaque identity/revision, namespace/date/core revision, source-revision lineage, append-only PIT facts, and bitemporal cutoff semantics.
- **Pre-change evidence:** migration 001 used `(publication_id, revision)` primary key; publication heads and child tables referenced that pair; lifecycle contract required fields absent from table; PIT contract declared implementation although no revisionable membership fact table existed.
- **Planned change:** add hash-checked forward migrations `003`–`007`; give each publication revision a unique opaque ID, explicit lineage/revision number, same-day parent and prior-session identity constraints; bind state heads and namespace cutovers to full publication/head identities; add `security_membership_facts`; mirror and validate source revision timestamps/supersedes on lifecycle and membership facts.
- **Acceptance:** all seven migrations applied with verified hashes; PostgreSQL schema and negative-vector tests pass.
- **Next stage:** P0-3 Algorithm Contract validator.

## P0-1 / P0-2 — Acceptance evidence

- `V4_PHASE0_CONTRACT_ALIGNMENT_R2` applied transactionally; migration SHA-256 `e1e2886c04c45121530e1fcf506297921c9cca2eecec3ee06be77e2520887d77`.
- `V4_PUBLICATION_HEAD_REVISION_IDENTITY_R2` applied transactionally; migration SHA-256 `905af9323f613d3ae917000859f2306ce3d2a2ec6be43431233c5f4ce0e8a1b3`.
- `V4_STATE_AND_NAMESPACE_PUBLICATION_IDENTITY_R2` applied transactionally; migration SHA-256 `f7df9d66c6edb13e948cbd92888af140ad335cb2984b9b0078e5498eee1cb4a0`.
- Final schema: 15 V4 tables, 24 validated foreign keys, zero unvalidated keys, seven verified migration checksums, zero runtime rows.
- Schema tests: included in final `py -3 -m pytest -q tests\v4_phase0` run → 42 passed in 1.06 s.
- Acceptance: publication row identity is one opaque `publication_id`; same-day lineage has monotonic revision, same namespace/date, a single successor, and explicit prior-session publication/digest or gap reason. Lifecycle and PIT contracts are backed by real columns; PIT facts and correction chains are append-only and source-revision-linked.
- Next stage: P0-3 / P0-4 have executable validator and gate changes in place; complete full negative-vector run, then P0-5 / P0-6.

## P0-6 — Performance baseline pre-execution record

- **Stage contract:** V4.2.2 REV2 §74 requires measurements for components that exist; absent V4 modules are recorded `NOT_IMPLEMENTED`, and no values/thresholds are inferred. R2 forbids rerunning the 00D overlap workload.
- **Planned bounded sample:** hash-checked migration ledger timing, a 1,000-row temporary PostgreSQL write/read in a rolled-back transaction, before/after database size, current local legacy API/UI GET latency and payload only if already listening, and process CPU/RAM. No pipeline/scanner/source/download, no durable test rows.
- **Acceptance:** `reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json` records the final seven-migration rebuild: 1.02 s, 15 tables, 24 validated FKs; temporary database removed and database set unchanged.
- **Next stage:** P0-7 audit-truth correction and R2 receipt/gate reissue.

## P0-3 / P0-4 — Acceptance evidence

- **Contract:** R2 §§5–6 and §12; REV2 §72–73 and §81.4.
- **Evidence:** framework/registry exact schema cross-validation, required parameter metadata/statuses, `requiredness`/`nullable`, compare/arithmetic operator+arity, enum identity/version, section schemas, field references, malformed negatives, and scope-level tests. An earlier run passed 42 in 0.82 s; final post-migration verification passed 42 in 1.06 s.
- **Acceptance:** P0-3 `FULL_PASS`; P0-4 no status-only permission inference. Required V4-01 scopes must be explicitly accepted.
- **Next stage:** P0-5 / P0-6.

## P0-5 / P0-6 — Acceptance evidence

- **Contract:** R2 §§7–8; V4.2.2 REV2 §74.
- **Evidence:** marked-relative thresholds/matrix remain unset and disabled; final performance receipt records isolated fresh rebuild, rolled-back PostgreSQL write/read, DB size, CPU/RAM, ledger timing, and V4/legacy endpoint unavailability. 00D runtime was not rerun under R2's explicit prohibition. Final suite: 42 passed in 1.06 s.
- **Acceptance:** 00H `DEGRADED_PASS`; `MARKED_RELATIVE_BENCHMARK_CONSUMER` blocked, RAW Bootstrap unaffected. Not implemented/not available metrics are explicit; no invented SLA or threshold.
- **Next stage:** P0-7 and final scope-level receipt.

## P0-7 — Audit truth and acceptance role

- **Contract:** R2 §9.
- **Evidence:** the earlier conversation explicitly requested a physical backup before database deletion. The repair card's claim that the backup was unrequested conflicts with this source record.
- **Acceptance:** keep the accurate `USER_EXPLICITLY_REQUESTED` history; classify the backup as `INFORMATIONAL_NON_AUTHORITATIVE`, not an acceptance prerequisite. No false audit correction is made.
- **Next stage:** external audit of this R2 package; do not start V4-01 before that review.

## R2 final acceptance

- Gate result: `DEGRADED_PASS`; V4-01 entry: `AUTHORIZED`; Scanner: `NOT_APPLICABLE_UNTIL_V4_05`.
- Accepted scopes: `A_STOCK_TDX_SOURCE, LIFECYCLE_SCHEMA, PUBLICATION_IDENTITY, RAW_BOOTSTRAP`.
- Blocked scope: `MARKED_RELATIVE_BENCHMARK_CONSUMER`. Required blocked scopes: `NONE`.
- Core blockers: NONE. Stage/final receipts are the canonical machine evidence.
