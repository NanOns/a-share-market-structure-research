---
stage_id: V4_R21_R4_DAILY_EXECUTOR_PG_CALENDAR_HEAD_R85_20261017
branch: codex/v4-workspace-cleanup
status: DAILY_EXECUTOR_ACCEPTED_DATE_PG_ONLY_CODE_VERIFIED_LIVE_HEAD_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Daily executor accepted-date Head source

`operational_daily_executor_v1._accepted_trade_date` no longer reads `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json`. It requires `v4_market_calendar_reader_r1` to return an accepted calendar sourced from `PG_ACCEPTED_PUBLICATION_HEAD`; explicit `V4_MARKET_CALENDAR_SOURCE=FILE` now fails closed. The exact original stable ID `V4-BCA-R2-928e5423aa7c5ec455a8` was updated with this new evidence. It remains in `IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION` because live database identity, canonical Head/publication equivalence, namespace and T0 were not available.

Verification: **23 passed** across the daily executor, calendar PG progress, old-identity preflight and pre-next-T0 executor chain. Controlled calendar fixtures verify the consumer path and FILE rejection; they do not establish live publication acceptance.

Original accounting remains **0/266 formally complete; 266/266 remaining**. Code-level PG paths pending live reconciliation: **53**; OPEN: **203**; ingress-open: **10**; open or ingress: **213**; unmapped reference edges: **22**. No live PG access or write was attempted.

Next: remove explicit FILE fallbacks for BaoStock runtime acceptance and official session/calendar consumers, then continue migrating current Head and Owner reads with exact relation and T0 bindings.
