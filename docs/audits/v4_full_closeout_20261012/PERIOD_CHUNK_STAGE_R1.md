# Period PG storage stage, 2026-10-12

Contract: CORE_PRODUCT_PERIOD_PG_OWNER_R1 / ORDERED_PG_PERIOD_CHUNKS_R1.

The complete 2026-09-28 reconstruction retained 5,222 per-security checkpoints. The original single-payload INSERT exceeded its bounded 120-second statement timeout. No production Head or authority was promoted. The replacement writes append-only chunks of at most 1,000 rows and an ordered manifest. Consumers verify native database identity, descriptor and actual payload SHA, date, domain, Head, offset, row count, and all immutable source bindings. Readback uses read-only transactions without migration DDL. No row is excluded and unknown status remains unknown.

Evidence on G: `G:/codex_tmp/v4_full_closeout_20261012/period_owner_0928_r2b.log` (original INSERT failure); `period_owner_0928_r2c.log` (isolated PG unavailable); `pg_recovery_r1.log` (isolated crash recovery); `denominator/chunks_r2.xml` (real PG ordering, all 2,003 fixture rows, null preservation, cross-date rejection, actual chunk corruption rejection; 1 PASS). The first chunk test failed due to a missing read-only DSN attribute and remains preserved in `denominator/chunks_history_r5.xml`; the corrected test supersedes that specific failure.

Acceptance: storage invariant test PASS. Complete dated reconstruction readback and independent numeric oracle remain required. This stage is not full V4 acceptance, formal PG role acceptance, PIT/AS_RECORDED permission, or production cutover.

Next: complete all dated owners, their independent numeric/quality oracle, remaining current governance issues, legal full regression and formal deployment hard gates. Desktop-only localhost scope applies; narrow-screen/mobile demonstration is excluded by the user's explicit instruction.
