# V4-05 R4.1 Closure Candidate

Stage: `V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE`

Candidate: `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_1`

Independent postcheck: `PASS`

External acceptance: `PENDING`

## Closed in this candidate

- **B03 PostgreSQL ledger:** PostgreSQL psql (PostgreSQL) 18.6, 12 formal migrations, isolated database, no production connection, I01–I05 passed, transaction rollback and cleanup verified.
- **B05 canonical identity:** governance JSON now uses `CANONICAL_JSON_SHA256_V1`; the V4-02 global accepted binding remains `83fa37ded40337d69ff0e447a0b6a3bc293d2ca95ea9c8aa009f0f104776c4be` and matches the reconstructed frozen representation. Protected accepted heads are unchanged.
- **Determinism:** the pushed implementation commit `bdc2f65a09efc006fe9ca5806f3d5b244b564f42` was rebuilt in a fresh remote clone after LFS fetch/checkout. All 10 required generated outputs have identical bytes and logical projections.
- **Published LFS payloads:** fresh-clone restore for candidate commit `be1f3e35068b5be6519dca2ea4293df74c8d992a` is `PASS`; all R4.1 LFS output OIDs, sizes, and restored bytes match.

## Business values remain frozen

- 2026-09-28 target, 5222 target identities, 5222 core-profile rows.
- Market reference returns: 1 session `-0.022314506957301243`, 3 sessions `-0.03792535346523633`, 5 sessions `-0.01769091161662751`.
- R4→R4.1 differences: business fields 0, states 0, unexpected drift 0.
- `CURRENT_FORWARD_STOCK_CORE=DEGRADED_PASS`.
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`.

## Candidate boundary

This is a stage candidate, not an external acceptance. No `data/v4/V4_05_ACCEPTED_HEAD.json` was created, `V4_STAGE_ACCEPTED_HEAD` remains unchanged, and V4-06/V4-07 were not started. The next action is independent external audit for R4.1.

See `V4_05_R4_1_INDEPENDENT_POSTCHECK.json` and `V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json` for hashes and checks.
