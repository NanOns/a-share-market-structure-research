# V4-05 Replay Gate A R4 Closure

**Stage result:** `DEGRADED_PASS_CURRENT_FORWARD_STOCK_CORE_CANDIDATE_R4`  
**External acceptance:** `PENDING`  
**Implementation commit:** `0e5b7585c5bd1e332ce6d11c6dfd1e4ff6cb6108`

R4 repaired the contract and identity defects found by the R3 external audit without rebuilding or rewriting the accepted source/adjustment main chain. It restored `PERIOD_ASOF_V1` temporal view semantics, bound 1/3/5 market references to accepted V4-01 start provenance and endpoint-specific basis identities, created the date-qualified Sep-28 target snapshot, and rebuilt the Core Profile with those repaired identities.

The V4-03 market path has a frozen `UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION` policy. R4 therefore chose Option C: no Sep-28 accepted-series path row was published, target `trend_axis` is `UNKNOWN`, and the Market Regime is `DEGRADED_PASS`. A separate 25-session current-coordinate diagnostic quantifies path differences and leaves all accepted V4-03 path rows unchanged.

The isolated revision ledger replay passed I01–I04 with observed query counts and successful cleanup. Remote LFS restore evidence is pending the fresh clone of the pushed artifact commit and will be bound in the final R4 candidate manifest.

The 423-test regression suite passed with 2 skips, the independent numeric postcheck passed 65 samples across four boards and required data states, and the six primary R4 artifacts reproduced byte-for-byte on the second build. The R3→R4 profile diff preserves all 5,222 rows with zero unexpected business-value drift.

Historical `AS_RECORDED` remains `BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`. Both `data/v4/V4_STAGE_ACCEPTED_HEAD.json` and a V4-05 Accepted Head remain unchanged; no later-stage authorization is included. Stop here for independent external R4 audit.
