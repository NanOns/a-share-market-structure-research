# Actual 28765 browser matrix — old production process

IAB now successfully accessed localhost. Six entrances at 1366×768 and 1920×1080 have actual loaded DOM and viewport PNGs under `browser/`; heading visibility was awaited before capture. Each retained current T0 2026-10-09. This is old PID 41528, not new-code deployment acceptance.

| Check | Actual outcome |
|---|---|
| home | 5224 stocks, 400 sectors, four-axis states visible; scoped available data |
| sectors / stocks / focus / diagnostics | loaded DOM captured; sources and gaps retained |
| market | SOURCE_INCOMPLETE for DATED_OPERATIONAL_MARKET_BREADTH_OWNER; HTTP200 does not make indicators ready |
| pagination | stock page 1→2→1, 5224 rows |
| search | 301628 returns exactly one row |
| state filter | 启动确认 returns 461 rows |
| 301628 10/09 | 97.550, validity 失效 visible; old timeline is not evidence of corrected new Focus termination |
| historical 688349 9/30 | actual HTTP close=13.24; browser frozen-replay route SOURCE_INCOMPLETE, no 13.240 browser pass claimed |
| chart | old process reports missing chart Owner |
| breadth503 isolation and recovery | NOT_TESTED in production browser; supported browser surface has no request override, no production fault injection attempted |
| new-code FP13 | NOT_ACCEPTED_PENDING_NORMAL_CLOSE_AND_RESTART |

`browser/matrix.json` lists twelve captures. These are actual browser observations, not HTTP excerpts fabricated as DOM. Unchanged old fault tests are inherited only within their former engineering scope.
