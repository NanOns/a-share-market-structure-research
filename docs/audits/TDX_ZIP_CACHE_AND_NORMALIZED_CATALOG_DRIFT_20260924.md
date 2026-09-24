# Audit: TDX official ZIP CDN cache lag and normalized artifact catalog drift

Date: 2026-09-24
Status: `FIXED_WITH_FOLLOWUP_GATES`

## Scope

The online info endpoint reported the official daily package update at 2026-09-24 15:57:21, while the bare package URL returned a cached September 23 ZIP. After the September 24 package was accepted and M4 regenerated the normalized parquet, PostgreSQL artifact catalog still pointed to the prior file digest. Together, these prevented the expected daily Focus run.

## Evidence

- `HSJDAY_SOFT_TIME`: `2026-09-24 15:57:21`.
- Bare official ZIP URL response: Last-Modified `2026-09-23 15:57:01` Beijing time; content omitted September 24 records.
- Same HTTPS host and ZIP path with unique cache-busting query: Last-Modified `2026-09-24 15:57:21`; new ETag and size; downloaded package validated through M3 as `FULL_PASS` for 2026-09-24.
- Accepted publication: `m4-4c7e20b9b986cc6e193df851b764adce`; source bundle `6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2`.
- Rebuilt normalized parquet: SHA256 `c6fc7b5455355390b0740b46e4bf24a2c5f458084cd6155478eae6c0be75c05a`, cutoff 20260924. PostgreSQL had retained a prior SHA; sync now registers the exact-date file and marks prior same-path references stale.
- Focus preflight, real transaction rollback, apply, and PostgreSQL readback evidence are in `reports/upgrade_m3/FOCUS_20260924_CONTINUATION_ACCEPTANCE.json`.

## Fixes

- `run_upgrade_m3.py` adds a unique query parameter to the official ZIP request. The downloader continues to enforce the approved HTTPS host/path.
- `scripts/sync_latest_publication_to_postgres.py` validates parquet cutoff before catalog registration, retires stale same-path references, and commits the current SHA with publication sync.
- Focus M9 frozen basket handling now ignores provider extras and retains missing frozen members as unknown for the existing coverage gate; it does not invalidate a whole daily batch for a harmless superset or a local missing member.

## Acceptance

`DEGRADED_PASS`: Official September 24 records accepted, 23→24 Focus head lineage is valid, real rollback left all 14 Focus table counts and head identities unchanged, and committed readback contains 397/397 observations and 397 projection rows. Outcome settlement is `READY` with 310 pending horizons; 323 observations carry `DATA_UNAVAILABLE`. Those are tracked follow-ups, not silently converted to positive or negative facts.

## Follow-up

Track due outcome settlement as later sessions arrive; investigate the provenance gaps behind `DATA_UNAVAILABLE`; keep automatic apply disabled until multi-day and due-outcome acceptance gates pass.
