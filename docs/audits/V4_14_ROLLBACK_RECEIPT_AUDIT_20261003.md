# V4-14 rollback receipt P0 disposition

Baseline: f7b3402e4fbd5c98f4e76e3a56042a84960e120a. The four exact task documents are imported under docs/evidence/r18_rollback. The master schedules A then B, clean detached validation, unified commit/push and STOP.

G01 is a separate cross-cutting audit item: the active V4-14 contract requires a rollback receipt. Its scope is isolated candidate activation, with no production cutover or formal acceptance. Existing r5 runtime, mappings, trajectory, consumption oracle and real evidence are frozen inputs.

A executes RB01-RB08 in dedicated sandbox copies. It reuses accepted V4-13 atomic and append-only IO, pins exact predecessor bytes, archives the parent before activation, and performs exact bytes/hash CAS under an exclusive sandbox lock. Rollback checks candidate integrity and the current simulated pointer before atomic restoration. Corrupt predecessor test copies are rejected; recovery uses the undamaged immutable parent archive. All final sandbox heads equal the predecessor. A second rollback is idempotent. The failed candidate remains immutable evidence.

B independently derives expected predecessor, protected files and all r5 evidence from the audited Git baseline blobs. It never calls rollback code to calculate expected outcomes. It checks isolated paths, CAS observations, activation/failure/restoration snapshots, parent archives, policy failure fields, retained evidence, idempotency and permissions. Fourteen mandatory receipt attacks, six permission attacks and implementation fail-closed tests accompany the oracle.

The canonical receipt is reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json. The final seal binds it to the unchanged r5 candidate, independent consumption and rollback oracles, negative gate and clean regression. No r5 replay generation occurs in this round; inherited regression tests validate retained evidence and their existing disposable fixtures.

All six real protected files remain byte-identical. No V4-14 Accepted Head, Stage/Data advance, Replay Pass, production/shadow/focus, V4-15 or raw/provider fallback is granted. Real evidence remains capability-scoped, with historical PIT NOT_GRANTED. Local PASS requires final independent audit; NEXT is STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT.
