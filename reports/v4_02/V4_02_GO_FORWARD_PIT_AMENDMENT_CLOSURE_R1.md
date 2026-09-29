# V4-02 go-forward PIT amendment candidate R1: blocked closure

Starting HEAD: `52ff45b138fa536e802168a11aebbba6d1cb1d9d`. Target: completed trade date `2026-09-28`.

## Stage contract and evidence

The new task and external audit are sealed under `docs/evidence/`. Entry contract: `V4_02_GO_FORWARD_PIT_AMENDMENT_STAGE_ENTRY_R1.md`. Source gate: `V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_R1.json`. TDX capture attempt: `V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R1.json`. The Sep-26 GBBQ snapshot manifest and its `gbbq`/`gbbq.map` hashes were verified; `system_available_at=2026-09-26T13:07:05Z`, first eligible formal date Sep-28.

At 2026-09-29 14:38 Asia/Shanghai, the official TDX update info advertised a Sep-28 package, but bounded capture returned `TDX_ZIP_INVALID`; no validated package was persisted. The project-controlled Sep-28 package count is zero. Read-only inspection of local `D:/new_tdx/vipdoc` found zero SH and SZ `.day` files ending at Sep-28 (SH latest last-record date Sep-18; SZ Sep-24). This cannot establish a complete Sep-28 close. Independent postcheck separately confirmed the missing package, local counts, GBBQ manifest identity, and historic-block label.

## Acceptance result and limits

Terminal status: `V4_02_GO_FORWARD_BLOCKED_NO_COMPLETE_20260928_RAW`. No raw source snapshot, overlap verification, incremental universe, QFQ adjustment, full-market quality counts, deterministic double build, no-backdating result, or later-snapshot revision comparison can be claimed. These gates are `NOT_RUN_BLOCKED_BY_RAW_SOURCE`. `GO_FORWARD_PIT_ADJUSTED_PRICE` is **not accepted**; the requested amendment candidate was **not produced**. `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE` remains unchanged. Existing V4-02, V4-04, and global Accepted Heads were not modified. TDX root write count: zero.

## Next stage

Acquire a valid, immutable, independently verified complete Sep-28 raw source snapshot under a separately versioned attempt, then perform overlap, universe, adjustment, determinism, temporal negatives, and independent postcheck before external audit. Do not promote or run V4-05 R2 on this blocked result.
