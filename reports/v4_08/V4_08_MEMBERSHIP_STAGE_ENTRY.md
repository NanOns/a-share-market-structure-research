# V4-08 PIT Sector Membership Baseline R1 — Stage Entry

- Stage contract: `V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1`.
- Workstream task: `V4_06_V4_07_PROMOTION_AND_V4_08_MEMBERSHIP_BASELINE_STAGE_TASK_20260930` (SHA-256 `a957947d7fc0329523ada4be06a6a7a9395d3426a2acc2ed24b0e52a1220d175`).
- Starting commit: `6f2c1fa`, branch `codex/v4-system-reform`; V4-07 Accepted Head SHA-256 `b22117b0d14c35167cba86cb7398d878d7112f9cf17c1a427fa92766e78f880f`.
- Applicable contract: `A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`, especially §77C and §78. Ownership amendment: `V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1_20260929.md`.
- Phase 0: `FULL_PASS`, inherited from the global accepted head. V4-07 external engineering acceptance is bound; real Base Seed signal remains degraded by the open prior-RPS bootstrap audit.

## Source review

Latest accepted session available from the V4-02/V4-05 chain: `2026-09-28`; formal publication time: `2026-09-29T06:53:52Z`.

Read-only source inspection of `D:/new_tdx/T0002/hq_cache`:

| File | SHA-256 | Local filesystem modified time |
|---|---|---|
| `tdxhy.cfg` | `f0861020e5d9fde9f10ab0374da6b887f3a5f681cfa00bb7dc6776ee4703c735` | `2026-09-28T22:28:35.142383+08:00` |
| `tdxzs.cfg` | `a33983fc8bb15c97db93fe9b60394b326b71a91e99e33b8b54700415442074da` | `2026-09-24T17:53:12+08:00` |
| `infoharbor_block.dat` | `025d9ae0c50d0cbf64fa3ba06c419681d7a931a9192b1c7841b14382b53b7595` | `2026-09-28T22:28:34.808829+08:00` |

Filesystem modified times are not provider availability or project ingestion receipts. No system-availability evidence binds these membership files to the 2026-09-28 cutoff, so they cannot prove PIT membership for that date. The source root remains read-only.

Initial raw scan: 87,937 rows; 0 duplicate source facts; 12,639 `index_group` rows; 5,965 distinct source security keys. Of those keys, 497 are not resolved by V4-01 records (101 unresolved candidates, 380 non-core candidates, 16 absent). Preserve these rows and fail closed for formal materialization.

## Entry result and next stage

- Authorized now: freeze versioned membership/type/quality contracts, V4-owned append-only PostgreSQL schema, and diagnostic replay/leakage/revision/determinism gates.
- Not authorized: historical PIT claims from current membership, full-market Sector/Rotation production, or coercing unknown Seed-dependent fields to zero.
- Entry result: `AUTHORIZED_FOR_MEMBERSHIP_BASELINE_ENGINEERING_ONLY`; PIT baseline remains unproven.
- Next: seal the prerequisite evidence, then stop for independent external membership audit before any dependent production.
