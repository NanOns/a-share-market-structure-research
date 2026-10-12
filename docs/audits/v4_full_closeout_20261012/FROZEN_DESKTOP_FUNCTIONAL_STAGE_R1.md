# Compiled desktop functional stage, 2026-10-12

Latest user cutover amendment applies: performance and production rollback tests are deferred; desktop localhost only. They are not cutover gates.

The actual Windows executable started against `G:/codex work/v4-production-20261012`, port 28871. Evidence: `G:/codex_tmp/v4_full_closeout_20261012/formal_frozen_status_r1.json` and `formal_http_functional_frozenr1/RESULT.json`. Six desktop routes and related APIs returned HTTP 200; actual engine RUNNING, scheduler disabled, stock count 5224, sector count 400, Focus count 2805, common context token `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`.

This is compiled-entry functional evidence, not full production acceptance. The package resource source SHA is `a2ebdaeb672e4ebf99b8b34697964a2408bdc2b4234fd4574fbd7b25f2fdc7e5`; a final package must bind the final frozen Git revision. Old production has not been switched.

Full regression R1 retained 5463 tests: 4975 PASS, 269 FAIL, 157 ERROR, 62 SKIP. Exact failure/error/skip rerun FULLFIXR1 retained 488 nodes: 234 PASS, 220 FAIL, 34 ERROR. FULLFIXR2 reruns all remaining 254 nodes after missing-input recovery and test-fixture repair. These subsets do not replace the full denominator or establish full PASS.

The E5 legacy engineering fixture now uses the already admitted isolated `fep_e1_upgrade` database on port 55793, matching its existing fixture guard. The settlement corruption fixture uses PostgreSQL DROP TRIGGER syntax for the disposable native database, preserving the historical SQLite syntax only when native mode is disabled. Original corruption and rejection assertions remain intact.

Next: complete dated native PG period publication/oracles, remaining functional regression repairs, full consumer/field acceptance and final compiled default entry verification. Direct production cutover is authorized only after genuine functional/data gates pass; actual hard failures retain old production with concrete evidence. Include the amendment and preserved evidence in the single G-local final delivery package.

Follow-up verification: FULLFIXR2 retained all remaining 254 nodes, with 48 PASS, 194 FAIL, 12 ERROR. Native home fixture `home_pg_r3.xml` passed all 4 original display assertions; native settlement `settle_pg_r4.xml` passed all 13 original corruption, idempotency and revision assertions. Deliberate malformed rows bypass only disposable-fixture constraints; deployed schema guards remain unchanged. Corrected evaluation-source fixtures now bind actual immutable file bytes rather than fabricated digest values. These focused passes do not supersede full regression.

2026-09-30 period independent aggregation oracle completed 18,320,640 checks with zero differences (`period_oracle/R1/2026-09-30/RESULT.json`). Its scope is aggregation only; adjustment-factor acceptance remains separate. 2026-10-08 native publication completed both domains, 5224 source securities, exact complete payload readback; independent aggregation oracle is running. No production switch, performance test or production rollback test was performed.
