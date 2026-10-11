# R4 isolated execution contract

Authority: R4-MASTER-R1 (2026-10-11), user request to execute the supplied card.
Base/origin: fbd23a6ba08d0948fe7ad421d1765fe363648522.
Owner: Codex / root. System: EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE.

R4-00/01: freeze original 245 modules/4568 cases, review both included and excluded modules using entry evidence. AST output is explicitly a candidate superset. No scope acceptance until dynamic callers and per-module contract evidence are complete. Separate production-loaded evidence from source existence.

R4-02: isolate native psycopg job store under explicit V4_NATIVE_PG_DSN and per-workspace schema. Preserve old SQLite sources; no runtime fallback. PG transactions replace BEGIN IMMEDIATE with a schema-specific transaction advisory lock; PG session advisory worker lock covers execution and releases on process exit. Pending physical restart and migration oracle gates must remain open until measured. Conflict updates apply only to dispatch/rearm projections; attempts/events remain append-only.

R4-03: native PG immutable history versions tied to head digest, T0, original history source and logical payload digest. Keep accepted v0.2 prices. New candidate bindings; no modification of accepted pack. Same HTTP chart transform, aggregation and paging semantics. Complete 5224-symbol and five-date browser comparison remain required for package acceptance.

R4-08: v0.3 exact coefficients must be present for exact computation; source-digest-bound typed transport, invalid input rejection. Old v0.2 module unchanged. Full consumer/PIT impact gates remain independent.

R4-09 FA-020: newline index optimization only, compare complete scan_file receipts against frozen implementation on Unicode/CRLF/SQL/JSON/MD and dense matches. Preserve classification and hard gate. Homepage capacity gate has no authorized threshold and remains OPEN.

R4-06: fail-fast nonbusiness exception plus per-node connection ledger. Original PASS is semantic replay required; no blanket skip, no whole-repository pytest, no legacy V3 regression. Full clean run only after corresponding candidate readiness.

R4-04: stage native PG snapshots with publish=False only; compare all objects/aliases/members and metadata semantics against a frozen read-only source oracle. Candidate descriptors never replace accepted authorities. Actual producer errors are retained as failed evidence. Joint publication, historical-date reads and rollback must each be verified independently before admission.

R4-05 / DB-10/11/12: review stock series, Focus journals and optional shadow readback as distinct persistence capabilities. Native Focus journals use a shared PG registry, transaction advisory lock and PG CAS; immutable version schemas are historical business data, filesystem descriptors are audit bindings. Concurrent stale writers must fail rather than overwrite the accepted registry. A failed descriptor export cannot make the filesystem the business authority. Optional old SQLite shadow bindings fail closed until explicitly migrated.

R4-10 engineering fixture increment: replay existing FEP E1 schema/visibility/revision contracts in fep_e1_fresh on an independent G cluster at 127.0.0.1:55792. Apply unchanged SQL 001--033; permit only explicitly registered database/port/directory/admin identities, attest every registered database before test admission. A first attempt to create a second schema-complete database on 55791 failed on cluster-global duplicate roles; that transaction rolled back. Use a fresh cluster rather than edit or skip frozen SQL. Every fixture is synthetic ENGINEERING_FIXTURE and rolled back. This does not grant PIT, real label maturity, OOS, production deployment or source-writer permission. Scope remains a named subset pending the complete legal denominator.

Acceptance is evidence-specific. Next stage is isolated integration after readiness, followed by independent external review; production switch, Windows installation, PIT/Grant/OOS are not authorized by this task.

R4-03 explicit isolated HTTP authority increment: source_root remains original accepted read-only root; index_root is attested G isolated PG workspace. The optional authority is contract-versioned, token/T0/source-digest/schema-bound and confined to the exact engineering subtree. Default production authority is untouched. D/W/M and RAW/QFQ queries use actual product handler/BFF/reader; missing historical period owner returns SOURCE_INCOMPLETE rather than iterable crash. Wrong token and non-PG authority must be rejected. All isolated responses explicitly production_accepted=false. Latest SQLite chart oracle executes frozen original implementation in a separate process with mode=ro; source/schema/data byte protection remains independent.

R4-05 / DB-06 pure rank capability increment: extract _exact_cycle_delta without formula changes into V4_PURE_RANK_WINDOW_COMPARISON_R1. Operational V4 rank producer imports this pure module; leave frozen legacy builder and provider behavior intact. Preserve existing next-stage V4 business assertion node, switch its import to the V4 helper. Verify AST identity and known comparable/noncomparable/future-date bounds under native guard. This proves only the rank helper capability, not all legacy repository reachability.

R4-02 owned worker crash increment: explicitly synthetic ENGINEERING_FIXTURE PG job; hard-kill only owned child after actual durable checkpoint. Concurrent child must reject advisory session ownership before executor call. Restart must acquire released lock, preserve checkpoint and skip earlier PUBLISHED fixture date. No source factory is replaced for production proof; executor is explicitly a fixture, so actual source-stage CAS/resume and real accepted-T0 remain open.
