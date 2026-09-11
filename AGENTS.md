# Project guardrails

1. `D:/new_tdx` and every configured TDX source directory are read-only inputs.
2. Never create, modify, rename, or delete a file under the TDX root.
3. Phase 0 must finish with `FULL_PASS`, `DEGRADED_PASS`, or `BLOCKED` before scanner work begins.
4. M14 online enhancement is allowed for the approved public-source datasets through versioned source contracts, explicit per-dataset capability gates, auditable timestamps, bounded requests, and fail-closed degradation. It must not use external adjustment services, future data, automated trading, or probability claims; it must not alter local snapshot identities or block the local main flow. M14 hot-rank direct mode is request-time only: no hot-rank raw payload, row, batch, or historical snapshot is persisted.
5. Every factor and scanner must have an explicit, versioned contract and explainable output.
6. Project artifacts are written atomically outside the TDX root.
7. Before executing each stage, consult the latest applicable upgrade document and record the stage contract, evidence, acceptance result, and next stage; tests alone do not establish release readiness.
8. Cross-cutting or comprehensive audit issues (for example, M10 Amount A, but not limited to it) must be opened and tracked as separate audit items, with scope, evidence, and acceptance independent from the current stage gate.
