---
stage_id: V4_R21_R4_PROFILE_CORRECTION_OWNER_MANIFEST_PG_R80_20261017
branch: codex/v4-workspace-cleanup
status: PROFILE_CORRECTION_AUTHORITY_MANIFESTS_PG_ONLY_CODE_LIVE_HEAD_RECONCILIATION_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 52
open_callsite_rows: 204
ingress_adapters_open: 10
remaining_open_or_ingress: 214
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Profile correction authority manifests in PG

This batch moves semantic and dependent Profile correction authority manifests from runtime `AUTHORITY.json` reads to the existing append-only `authority_manifest` fact relation. The Head candidate binding now carries the exact PG descriptor inline. Each dated correction row descriptor is also embedded in that manifest, so runtime descriptor validation and correction reads do not reopen descriptor files.

`prepare` remains the explicit first-ingress path: it reads each source-bound correction patch, appends its rows, validates a PG readback, then appends the authority manifest. Runtime `load`, `apply`, field binding and cached attestation resolve the manifest through `read_authority_manifest`; missing bindings fail closed. Historical predecessor candidate files are still read by `conserved_dates` to prove append ancestry and remain open pending accepted-Head PG mapping.

## Stable-ID accounting

The original inventory remains **0 formally complete / 266 formally remaining**. Two exact Owner rows changed from OPEN to `IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION`:

- `V4-BCA-R2-a34870ce71af215d5654`: semantic correction `load` authority read.
- `V4-BCA-R2-4d72177931ccbfb8c6ff`: dependent correction `load` authority read.

Two source-ingress rows are now explicitly classified as active append adapters, not runtime Head consumers:

- `V4-BCA-R2-4e514a570663cb85be60`: semantic correction `prepare` source patch ingress.
- `V4-BCA-R2-a6637a1d93d5420c9ca1`: dependent correction `prepare` source patch ingress.

`V4-BCA-R2-760f46c21c917c652420` remains OPEN because historical predecessor file traversal in `conserved_dates` still needs exact accepted-Head PG mapping. The two source-ingress rows also remain open for source identity and live readback reconciliation. Across all 266 IDs: **52** code-level PG paths pending live reconciliation, **204 OPEN**, **10 ingress-open**, **214 open or ingress**, and **22 unmapped reference edges**. Owner subset: **48** code paths, **143 OPEN**, **9 ingress-open**; other-business: **4**, **23**, **1** respectively.

## Verification and limits

- **39 passed** across the new semantic/dependent authority-manifest boundary tests, append-scope conservation, Owner manifest controls, and contract-registry PG reader tests. These are controlled offline fakes and do not establish business acceptance.
- The combined attempt including the SQL parser test stopped during collection because the local environment lacks `pglast`; parser CI remains the SQL syntax gate.
- No live PG catalog/readback, DDL/DML, contract import, Head CAS, or business acceptance was run. Current runtime DSN presence checks remain absent. No production behavior is claimed.
- The contract-registry append-only approval event and staged historical-publication compatibility proposal remain unexecuted pending compliant read-only catalog reconciliation. The R75 DM-01 orchestration edits remain separate and uncommitted because staged repository policy flags report-backed dynamic business reads; no policy bypass was used.

## Next

Continue replacing accepted Head/predecessor and descriptor authority reads with their exact publication/Head PG relations; resolve Owner relation, namespace, T0 and source identity; continue DM-01 state ownership and TDX/BaoStock active-entrypoint path wiring. Keep the 266-item formal completion count unchanged until live identity and per-ID reconciliation evidence exists.
