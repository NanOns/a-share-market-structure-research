# V4-08 R4.1 Stage Entry

- Stage: `V4_08_R4_1_GENERIC_NO_SYMBOL_SPECIAL_CASE_REPAIR`.
- Date: 2026-09-30.
- Required starting HEAD: `0d959b24a44528265aff4784d8c283902f0abd3e`.
- Implementation HEAD: `60a18f9ce265a36547217c48dca3f3c0b2cd50a7`.
- Entry decision: `ACCEPTED_FOR_EXECUTION`; the external audit blocker is the scope of this repair.
- Exit acceptance at entry: `PENDING`; the evidence and result are recorded in the stage closure.
- Next stage after successful closure: independent external acceptance of R4.1. Do not create the V4-08 Accepted Head before that audit.

## Applicable documents

- R4.1 stage task: `docs/evidence/V4_08_R4_1_GENERIC_NO_SYMBOL_SPECIAL_CASE_REPAIR_TASK_20260930.md` SHA-256 `1aa37266202600ac33d9082007ae9825e36d5acaae0961be6acc31a9596a1032`.
- R4 external audit: `docs/evidence/V4_08_R4_INDEPENDENT_EXTERNAL_AUDIT_SYMBOL_GOVERNANCE_20260930.md` SHA-256 `c3d84debe03519031eddb5e529527d0f4e6f62473882c08c142721dc8cb41d36`.
- latest applicable upgrade: `reports/v4_08/source_contracts/REV4_FEP_R2_20260930.md` SHA-256 `203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`.

## Stage contract

1. Remove stock-specific behavior from all hard-gated runtime, system, governance-mutation, and runtime-configuration paths. Scripts default to `SYSTEM_PIPELINE`; audited exceptions require a source-hash-bound attestation and proven non-mutation/non-runtime properties.
2. Generic identity promotion must be reconstructed from authorized candidate events and change only `acceptance`; an independent verifier derives the expected rows from the parent, candidate, candidate head, and external authority.
3. PIT replay must use that generic identity artifact and preserve R4 source revision, snapshot, logical facts, artifact hash, row totals, and exclusion inventory.
4. Phase1 QA selection must be deterministic, board-stratified, based on current-universe cutoff bars and quality/history eligibility, with unchanged factor output digest. Phase0/TDX historical samples must be data-selected or isolated as evidence/test data.
5. Run the established stage test families plus the upgraded scanner suite in a clean detached checkout with disposable PostgreSQL, process-only DSN, no `config/.env` access, clean Git state before/after, and destroyed cluster.
6. Preserve `V4_00_TO_V4_07_ACCEPTED`; leave AUD-AMOUNT-A-06 as its independent cross-cutting audit item; do not create `data/v4/V4_08_ACCEPTED_HEAD.json`.

## Entry evidence and preconditions

- Phase 0 entry gate: `FULL_PASS` recorded in `reports/v4_08/V4_08_R4_STAGE_ENTRY.md`.
- Global accepted range: `V4_00_TO_V4_07_ACCEPTED`.
- The prior independent audit marks the P0 symbol-governance gate blocked; R4.1 is specifically scoped to that false pass and generic replay, without reopening PIT/AST research.
- No final V4-08 Accepted Head was present at stage entry.
