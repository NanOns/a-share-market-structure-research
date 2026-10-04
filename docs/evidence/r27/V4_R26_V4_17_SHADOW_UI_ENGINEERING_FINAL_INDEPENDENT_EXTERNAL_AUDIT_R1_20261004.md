# V4 R26｜V4-17 Shadow UI Engineering Independent External Audit R1｜2026-10-04

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `60b17524596918b66456fdd48dbc1beb068ab28a`  
Audited remote HEAD: `c1787b77e08a26e344d3cbb88148a60f93c3df3e`  
Exact tested source: `bf8784bf1f3b2e17a08f3f9b01145fdf99787984`  
Immutable tested tag: `refs/tags/codex/r26-shadow-ui-tested-source-20261004-r2`

## 1. Unique External Decision
```text
R26_EXTERNAL_AUDIT = PASS_FINAL_V4_17_SHADOW_UI_ENGINEERING_SCOPED

V4_17_UI_CONTRACT = PASS_EXTERNAL
V4_17_CONTEXT_IDENTITY = PASS_EXTERNAL
V4_17_READ_ONLY_API = PASS_EXTERNAL
V4_17_NO_REAL_DATA_BEHAVIOR = PASS_EXTERNAL
V4_17_SIMULATION_ISOLATION = PASS_EXTERNAL
V4_17_CONTEXT_NEGATIVE_MATRIX_U01_U18 = PASS_EXTERNAL
V4_17_EXISTING_UI_REGRESSION = PASS_SCOPED_NO_NEW_FAILURES
V4_17_REAL_STORAGE_SCHEMA_COMPATIBILITY = PASS_EXTERNAL
V4_17_TESTED_SOURCE_GOVERNANCE = PASS_EXTERNAL

R26_A01_INHERITED_V3_REGRESSION = OPEN_NONBLOCKING_HISTORICAL_DEBT

V4_17_ENGINEERING = EXTERNALLY_ACCEPTED
V4_17_REAL_SHADOW_READBACK = NOT_GRANTED_NO_REAL_PUBLICATION
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
V4_17G = NOT_GRANTED

R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
V4_17_ACCEPTED_HEAD = NOT_CREATED
Production = false
Focus source cutover = false
```

## 2. Change Scope｜PASS
R26 changes are limited to V4-17 Shadow UI contract/source config, read-only Shadow context reader, additive service routes, Shadow page/JS, tests and evidence. No V4-10～V4-16 business algorithm/runtime implementation was changed.

## 3. Read-Only Boundary｜PASS
All `/api/v4/shadow/*` contract routes are GET-only. The shared HTTP handler returns `405 SHADOW_READ_ONLY` for POST/PUT/PATCH/DELETE under the Shadow namespace. Tests cover attempted Focus pinning, production activation, cohort mutation and settlement mutation.

## 4. NO_REAL_SHADOW_DATA｜PASS
Current source config has `accepted_readback=null` and `external_acceptance=null`. The reader returns:
```text
NO_REAL_SHADOW_DATA
real_sample_count = 0
context = null
```
without opening SQLite. Tests explicitly fail if `sqlite3.connect` is called on this path.

There is no fallback to simulation, Legacy Focus, V3 production, latest file/DB, mtime or environment/query grants.

## 5. Simulation Isolation｜PASS
Simulation is constructor-injection only and must be labeled:
```text
ACTIVATION_SIMULATION
NOT_REAL_EVIDENCE
real_sample_count = 0
```
The production source config exposes no simulation switch.

## 6. Immutable Context Token｜PASS
The token freezes namespace, trade date, publication/revision, model/parameter/state lineage, daily-input digest, source-manifest digest, evidence origin and readback-manifest digest. All components must resolve the same token/context; deep-link, revision, date, namespace, origin and lineage mismatches fail closed.

## 7. Future Real Readback Path｜PASS
Real readback requires exact content-addressed accepted-readback manifest plus exact external-acceptance receipt. SQLite is opened `mode=ro` with `PRAGMA query_only=ON`.

The reader independently checks REAL/PIT_OBSERVED storage identity, SHADOW_V4 namespace, exact fact digests, publication/slot/state identity, model/state lineage, parameter set, source manifest and daily-input digest.

The accepted V4-16 real migration is structurally compatible: it exposes `storage_identity` and `facts(kind,id,namespace,execution_mode,evidence_origin,payload,digest)`.

## 8. Component / Quality Semantics｜PASS
Components: `summary`, `radar`, `entity`, `cohort`, `settlement`, `health`.

Unknown/pending/right-censored values cannot be promoted to KNOWN. KNOWN/DEGRADED values require source bindings. Settlement additionally checks exact outcome revision, right censoring and pending-vs-observed semantics. No BUY/SELL/recommended-position semantics were introduced.

## 9. U01-U18｜PASS
The negative matrix covers context-token/publication/revision/date/namespace/origin mismatch, cross-context components, simulation/Legacy/V3 fallback, latest/mtime discovery, UNKNOWN promotion, source-quality omission, stale outcome revision, right-censor misuse, Focus/production writes, mixed lineage and deep-link mismatch.

## 10. Existing V3 / Focus Regression｜PASS_SCOPED
Baseline:
```text
177 tests
174 passed
3 failed
```
Final clean source:
```text
221 tests
218 passed
3 failed
```
The exact same three historical failures remain; R26 adds no new regression failure. Therefore:
```text
R26_A01_INHERITED_V3_REGRESSION = OPEN_NONBLOCKING_HISTORICAL_DEBT
```
This is not a new V4-17 failure.

## 11. Tested Source Governance｜PASS
Annotated tag `codex/r26-shadow-ui-tested-source-20261004-r2` resolves exactly to commit `bf8784bf1f3b2e17a08f3f9b01145fdf99787984`. Final HEAD is one evidence-only commit ahead. No implementation drift exists after testing.

## 12. Protected State｜PASS
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED
V4_17_ACCEPTED_HEAD = NOT_CREATED
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
Production = false
Focus source cutover = false
```
R25 remains `WAIT_ACCEPTED_DAILY_INPUT`.

## 13. Stage Boundary
R26 grants only:
```text
V4_17_ENGINEERING = EXTERNALLY_ACCEPTED
```
It does not grant V4-17 final acceptance, V4-17G, Focus source cutover or production cutover.

REV4 requires formal V4-18 implementation/replay gate after the real Shadow gate. However §81.4 allows CONTRACT_DESIGN before implementation.

## 14. Next
```text
R27 = V4-18 MIGRATION REPLAY CONTRACT DESIGN ONLY
```
R27 may freeze migration, predecessor, open-episode, pending-settlement, namespace and rollback semantics, but may not execute migration or claim `MIGRATION_REPLAY_PASS`.
