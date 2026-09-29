# V4-07 Candidate Closure

- Terminal status: `V4_07_BASE_SEED_CANDIDATE_R1`.
- Acceptance result: candidate execution and required gates pass; independent external acceptance remains pending.
- Candidate: `BASE_SEED_V1`, target `2026-09-28`, 5,222 accepted identities.
- Accepted Core digest: `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`; candidate logical digest: `b2fba6054f93d5155198982cda10feab8a21c4239e94df7023b7dbca2b654cd1`.
- Required full regression: `533 passed, 2 skipped in 28.21s` on isolated disposable PostgreSQL 18.6; migrations 001–015 applied; temporary database and cluster removed.
- V4-06 isolation, determinism, machine vectors, independent source recompute, migration/rollback, and focused V4-07 tests passed.
- The current accepted inputs leave `rps5_delta3` UNKNOWN for all 5,222 rows and omit accepted T-1 close/MA20 fields. V4-07 retains these limitations as UNKNOWN.
- No accepted head was promoted. V4-08 is blocked pending independent external V4-07 acceptance.
