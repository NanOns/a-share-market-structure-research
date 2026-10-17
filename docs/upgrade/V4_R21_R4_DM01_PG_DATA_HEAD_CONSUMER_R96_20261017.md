# R96：V4 DM-01 continuous runner reads its Data Head from PG

## Scope

The V4 DM-01 stage-state reader now supports `data_head` and provides `read_latest_stage()`, which selects the latest ISO trade-date fact from the explicitly identified PG database and fails closed on missing, duplicate-latest, malformed, or digest-mismatched state. `append_stage()` accepts the Head's `accepted_trade_date` as its date binding.

`scripts/run_v4_continuous_data_maintenance.py` now obtains its current V4 Data Head from the PG stage-state fact path. Its local `V4_DATA_ACCEPTED_HEAD.json` read and the local Stage/Dev/bootstrap pointer creation path were removed from this runner. If PG has no Data Head fact, the caller exits with `DM01_PG_DATA_HEAD_MIGRATION_REQUIRED`; it does not consult a local Head as fallback. Runtime receipts identify the Head as `PG_FORWARD_FACT` and use its canonical payload digest.

## Verification and limits

- V4 DM-01 stage-state, continuous runner, and PG progress tests: **27 passed**.
- Coverage includes latest-date selection, duplicate latest Head rejection, exact PG identity/digest checks, and proving that a local Data Head file cannot satisfy a missing PG Head.
- No live PG read/write, DDL, DML, baseline import, Head CAS, or business acceptance was performed. The existing PG baseline stage facts are still required, and the live current Data Head import remains an explicit migration step.

## Original 266 stable callsites

No original stable ID is closed in this batch: **0 / 266 formally complete; 266 / 266 remaining**. The V4 runner's current Data Head consumer is now PG-only in code, but baseline inventory reconciliation and live migration evidence are outstanding. Stage/Dev baseline content and authorized migration remain separately open.

## Next

Prepare the exact, digest-preserving legacy Head import bundle and the minimum PG writer transaction/CAS contract without executing it. Continue the PG Head, Authority, descriptor, daily, and BFF call paths; keep actual PG import/publication behind separate authorization and do not claim business acceptance from controlled tests.
