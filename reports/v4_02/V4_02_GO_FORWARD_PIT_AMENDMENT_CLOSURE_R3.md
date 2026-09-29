# V4-02 go-forward PIT amendment R3 candidate closure

Starting HEAD: `0f66e88052b33b90ab76ec39bfeb115386f8bca2`. Implementation commits: `f89a5411bdf169d12f944e162f54c0f23bc0f5f0`, `7eab74af1871b8c17308dc97df544e121e995fb5`, `f6197db9a73f4584616db1af98bcf9c7e339493e`; runtime/postcheck commit: `288d306341d8c8879b090425677c35d84648176b`. Target 2026-09-28.

## U01 identity

R3 resolves accepted identities plus all target-date source keys through dated A-stock identity records. It fails closed for unresolved, future-listed, and ambiguous target keys. New listing provenance is carried into candidate rows. Synthetic tests cover valid inclusion and all three failure boundaries. Real Sep-28 source keys have no new listing; 5,222 accepted identities remain, with 5,210 T0 bars and 12 no-bar states. Required board counts remain SH_MAIN 1,702, SZ_MAIN 1,494, CHINEXT 1,408, STAR 618. R2→R3 row and business value diff is zero.

## T01 publication time

Each R3 row uses `PIT_OBSERVED_AFTER_FORMAL_PUBLICATION` and records target date, maximum source date, official raw publication, project raw capture availability, Sep-26 adjustment availability, and formal publication. Ordering is checked on every row. The official Sep-28 source was captured on Sep-29; earliest formal publication is the actual capture finish time `2026-09-29T06:53:52+00:00`. This does not assert Sep-28 intraday availability. Negative tests reject publication before raw/adjustment availability and future source dates.

## E01 runtime tests and R01 remote recovery

`V4_02_GO_FORWARD_R3_TEST_RECEIPT.json` binds implementation commit, exact command, source/test hashes, Python and dependency versions, start/end time and result: **401 passed, 0 failed, 2 skipped** across the required V4 test directories and new R3 tests. The isolated remote clone fetched the Git LFS object from origin, materialized 551,001,603 bytes and restored SHA256 `70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c`.

## Candidate and independent check

R3 candidate has 5,222 rows: `RAW_READY=5210`, `ADJUSTED_READY=5195`, unsupported/unknown event unavailable 15, and no-T0-bar unavailable 12. Frozen Sep-26 GBBQ remains the sole T0 adjustment input; later GBBQ is diagnostic only. R2→R3 comparison found no change to security IDs, source keys, raw or QFQ OHLC, quality, blocking categories or visible event digests. Determinism and no-backdating passed. Independent R3 postcheck passed accepted source/package identity, LFS recovery, publication ordering on all rows, candidate digest, diff, and unchanged Accepted Heads. TDX root writes: zero.

Terminal status: `V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R3`. External acceptance is **PENDING**. `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`. No Accepted Head was changed and V4-05 R2 was not started. Next stage: independent external audit; only a later task may authorize acceptance seal and V4-05 Replay Gate A R2.
