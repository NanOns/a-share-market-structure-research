# R28 V4-19 Focus Source Cutover contract design

Baseline: `94635fa369c60b3f8182cb4d813751a453682d88`. Exact tested source: `52b374c5721df9d5b6b70c88d1f7a6bce3f2adac`.

CUTOVER_V2 is frozen per capability: Shadow stable AND Forward AND externally accepted runtime Migration Replay AND all dependency permissions. R27 design acceptance does not satisfy migration runtime. Current production permissions are all false; no Focus route, accepted head or business authority changed.

The five capabilities have explicit dependency, fallback, UI, Focus and rollback policies. Stock requires 20 consecutive accepted market sessions, zero temporal/P0/identity corruption and a rollback drill, followed by at least five distinct signal dates and thirty distinct stocks with positive-event T5 OBSERVED outcomes. Controls/benchmarks require quality receipts. Sector/Rotation require separately frozen policies and never borrow stock counts.

The receipt schema pins exact identities, dependency scope and active gate receipts. Future cutover is atomic with route and dependency-head CAS. Mixed UI binds exact module publications into a shared immutable context manifest while retaining each module namespace/mode. Capability rollback preserves facts, user work and settlement ownership; affected dependent consumers fail closed and independent capabilities remain valid.

C01–C20 run only against synthetic design fixtures. Hypothetical permissions are never emitted as actual production grants or route changes. Static tests independently verify design expectations, thresholds, identity conflicts, quality degradation, deduplication and rollback scope.

Local and clean E-drive regression: 280 tests, 277 passed, the same three R26-A01 inherited failures, zero errors/skips/deselections. Existing tracked bytes and 109 unrelated untracked files are unchanged. LFS objects are independently hashed in the exact clean checkout. All project temporary space is on E:.

V4_19_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT. V4_19_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_GATES. NEXT = STOP_WAIT_R28_INDEPENDENT_EXTERNAL_AUDIT. Push is candidate publication, not external acceptance.
