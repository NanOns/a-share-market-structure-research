# R27 V4-18 Migration Replay contract design

Baseline: `c1787b77e08a26e344d3cbb88148a60f93c3df3e`. Tested source: `f7c7277a9cafb972b9f0a00829a5d3dcff0a1f81`.

R26 scoped engineering acceptance is carried from the supplied external audit. This local result covers contract design only; it grants no real Shadow readback, migration implementation, production Focus cutover, accepted V4-18 head or MIGRATION_REPLAY_PASS.

The namespace matrix inventories every repository SQL table declaration and explicitly separates declaration coverage from actual deployed storage authority. Native snapshot binding and user-work export remain future independently accepted inputs. Semantic carry mappings preserve predecessor/model lineage, original episodes/enrollment, frozen T0 controls/benchmarks, due obligations, outcome revisions and user ownership. Historical Shadow context remains immutable. Exact snapshot/final watermarks reconcile Legacy and Shadow gaps; rollback restores routing and retains accepted facts, user work and settlement ownership.

M01–M20 are declarative future runtime acceptance vectors. Six interfaces are frozen as design definitions with no production implementation. All five implementation-entry receipts remain absent; entry is BLOCKED_WAIT_REAL_SHADOW_GATE.

Validation: 24 static contract checks plus 221 existing UI/Focus checks; 242 passed and the same three R26-A01 historical failures remained. No tests were changed or deselected to hide those failures. The first authoring check found an incorrect test cardinality assumption about grouped rollback retention; the assertion now checks the required semantic set. No migration runtime was tested or executed. All pre-existing tracked files and unrelated work were verified unchanged. Temporary checkouts, pytest captures and caches use E:.

NEXT: STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT. Commit and push provide a reviewable candidate, not external acceptance.
