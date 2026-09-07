# Project guardrails

1. `D:/new_tdx` and every configured TDX source directory are read-only inputs.
2. Never create, modify, rename, or delete a file under the TDX root.
3. Phase 0 must finish with `FULL_PASS`, `DEGRADED_PASS`, or `BLOCKED` before scanner work begins.
4. No network data, external adjustment service, future data, automated trading, or probability claims.
5. Every factor and scanner must have an explicit, versioned contract and explainable output.
6. Project artifacts are written atomically outside the TDX root.

