# R17R1 authority repair scope

Baseline: 204d799f26a7badbce3d6b09d3ceed722c522c91. The attached master schedules A then B; external acceptance remains pending.

G01/G02 successors preserve DAG topology, time roles, owners, thresholds and quality semantics. Recursive closure additionally requires updating the DAG enrichment consumer and same-family field/output schema successors. Their object meanings are unchanged. Edge version metadata follows the corrected binding. A machine-vector successor moves retained R1 vectors into explicit historical_lineage; every vector input and expected output remains unchanged. These are transitive authority consistency repairs, not business redesign.

The r6 candidate and its original publication package remain immutable. The amended accepted entry has a separately recomputed active-package digest. The current Stage points exclusively to the amended head; predecessor head/package references are historical lineage. Current formal readers cannot fall back to the original head.

All 17 Replay dimensions, 60 literal vectors, temporal prohibitions, cross-process readback, exact previous market session, evidence classes and capability degradation remain unchanged. V4-14 v1.0 files remain historical immutable evidence. Whole-contract comparisons independently enforce authority-only changes.

The first A clean snapshot passed 876 tests. Subsequent validator hardening adds explicit authorized-family selection, exact leaf checks and baseline byte verification. The final B clean snapshot revalidates the entire A and B scope. No test is deselected. G01/G02/G03 are tracked separately in reports/r17r1a/audit_items.json with external acceptance pending.

No V4-14 runtime, accepted head, replay pass or production permission is granted. After unified push, STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT.
