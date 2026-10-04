# R29 V4-20 Default UI Cutover contract design

Baseline: `7f637644546a59b4cd28650def63be942f81b32a`. Exact tested source: `0e8281abb27bb17ea00d089422f0ac92a8e44f37`.

R29 freezes future UI semantics only. Current defaults remain Legacy production plus the explicit Shadow engineering page. Production permissions are all false; no router, default UI, Focus route, accepted head or runtime authority changed.

The six product modules and three dependent subcomponents have exact capability mappings. Composite containers never gain V4 through an empty dependency list. Required active accepted permissions resolve only an exact bound V4 publication; otherwise an exact Legacy route remains. Explicit Shadow is read-only and never a production fallback. Missing or mismatched exact bindings fail closed with UNKNOWN.

Mixed pages retain native sub-context namespaces and explicit mode/PROVISIONAL labels. Deep links pin old accepted contexts and remain historical read-only after cutover. Route/permission changes invalidate affected live caches and sessions rather than silently merging or rebasing. Focus writes require current V4-19 route, capability permission and exact endpoint identity/head agreement; Legacy authority and user product state are retained.

U20-01–U20-20 are synthetic design vectors, not UI runtime acceptance. U20-18 independently demonstrates Sector rollback affecting Rotation, Sector Risk Change and Stock Sector Dependent while Stock Core remains valid. R28 P2 coverage is closed locally, pending R29 external review; the frozen R28 contract remains unchanged.

Local and exact clean E-drive regression: 306 tests, 303 passed, the same three R26-A01 inherited failures, zero errors/skips/deselections. All existing tracked bytes and unrelated untracked files remain unchanged. Exact LFS objects are verified in the clean checkout. Project temporary checkouts, captures and caches use E:.

V4_20_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT. V4_20_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_PRODUCTION_PERMISSION. NEXT = STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT. Push publishes a reviewable candidate and grants no external acceptance.
