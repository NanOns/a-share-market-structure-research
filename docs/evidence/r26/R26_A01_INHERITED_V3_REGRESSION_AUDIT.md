# R26-A01｜Inherited V3 regression contract drift

Status: OPEN_INDEPENDENT_AUDIT. Scope and acceptance are independent of the R26 Shadow engineering gate.

The designated baseline `60b17524596918b66456fdd48dbc1beb068ab28a`, checked out cleanly on E, has three failures in the frozen 177-test Focus/V3 regression scope. The current source has the same three failures and no new failures. No existing test is skipped, deselected, weakened or edited.

1. `test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry`: the test expects the old `get('/api/v3/research/today?page='` JavaScript literal; the current accepted static script uses a later request construction.
2. `test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope`: its `_NoopService` mock lacks the already-required `status()` method.
3. `test_p01_01_lock_scope::test_send_marks_disconnected_client_closed`: the same mock mismatch occurs before the tested send operation.

Evidence: `reports/r26/baseline-final-tests.xml`, `baseline-final-summary.json`, `local-final-v3-tests.xml`, and the final clean regression report. R26's legacy AST equivalence test proves the original service module is identical after removing only new Shadow additions. V3/Focus static source bytes are protected separately.

The initial baseline probe also exposed two missing-DSN failures in already-mocked replay tests. Re-running baseline and candidate with the same non-secret, unreachable mock DSN reproduces the three failures above; no credentials are copied and no live PostgreSQL test is enabled. Initial outputs remain available.

Independent acceptance requires an authorized successor to reconcile those old assertions/mocks with the current V3 contract and re-run the entire frozen 177-test scope with zero failures. R26 does not close this item or claim an all-green comprehensive suite.
