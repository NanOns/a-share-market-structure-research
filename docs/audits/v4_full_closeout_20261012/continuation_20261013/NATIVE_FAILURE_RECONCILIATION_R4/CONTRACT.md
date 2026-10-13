# Stage 5 native failure continuation R4

Applicable upgrade: `docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`, B3.1–B3.6. Full native execution retained all 4,749 nodes: 4,689 PASS, 20 FAIL, 40 explicitly qualified historical-input SKIP. Every original failure is joined by its exact node identity to a passing continuation; no assertion, precision or denominator was removed.

Two synthetic reader fixtures now provide the current API fields (`api` and `candidate`). The two original pending-policy precision nodes preserve their exact original synthetic IO layer. One original all-inputs Extension vector remains a superseded historical contract; the current REV2 branch-specific semantics have separate actual numeric and missing-input controls. None of these historical checks admits current production.

Ten later failures shared an import-path leak: the historical width script prepended its old root to `sys.path`, and later validators imported from that unrelated stage. Scoped historical loading now restores the original import search path, and a per-node fixture also restores it at teardown. The actual trigger followed by all ten failed nodes passes (11/11); the six mutation/provenance controls also passed independently and as the original 45-node module.

Current policy source conservation checks all 54 primary bindings and all 604 component bindings: zero drift. Large accepted numeric calculations were not repeated. The original full failure XML, four focused XMLs and manifests are retained with SHA/size references in `RESULT.json`.

Acceptance: `PASS_EXACT_FAILED_NODE_RESOLUTION_ONLY`. This is explicitly **not** a uniform clean-slate full PASS. Historical 2,539-node execution is still running, and the final source freeze/full acceptance and original-port desktop cutover remain pending. Next: finish historical diagnostics, repair only dependent scope, then establish the final uniform frozen acceptance required by B3 before B4 activation.
