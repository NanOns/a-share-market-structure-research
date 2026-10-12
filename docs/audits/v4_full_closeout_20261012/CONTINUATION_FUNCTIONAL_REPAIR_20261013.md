# Functional continuation, 2026-10-13

Contract: V4_FULL_CLOSEOUT_FUNCTIONAL_CONTINUATION_R1. The complete local total task card was consulted, with USER_CUTOVER_SCOPE_AMENDMENT_20261012.md and USER_DESKTOP_LOCAL_ONLY_SCOPE_20261012.md taking precedence. Performance, rollback tests and mobile presentation are deferred. The original service at 127.0.0.1:28765 remains unchanged. No Google Drive access and no subagents.

Entry: clean codex/v4-full-closeout-20261012 at da339981; prior push was successful. Five-date period aggregation and formal transfers are completed evidence, not repeated. Latest full failure rerun FULLFIXR2 is retained with 48 PASS, 194 FAIL, 12 ERROR. Full denominator remains mandatory.

First repair: V6 SettlementObligationControllerR4R2 still opened a PostgreSQL descriptor using sqlite3. Its successor writer also lacked the native dispatcher already present in V5. Both now select the existing native PG implementation. The reader verifies descriptor, migration, schema and cluster identity and enforces read-only transactions. No grant or model authority is created.

Evidence: G:/codex_tmp/v4_full_closeout_20261012/denominator/A08R20261013.xml. Result: 11 PASS, 4 FAIL. Both actual V5/V6 startup compatibility assertions now pass. Remaining failures identify stale accepted source bindings and historical selection gates; they are not hidden by the repair. This record was written after the first targeted run; the task card and latest stage documents were read before that run.

Next stage: snapshot link-negative repair and targeted tests; then complete remaining frozen-input, native consumer and automatic daily source diagnosis, followed by the full frozen legal regression and authorized cutover only when functional/data gates pass. Full acceptance and production cutover remain false.
