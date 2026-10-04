# V4 R20R1R2 Final Independent External Audit R1｜2026-10-03

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`

Branch: `codex/v4-system-reform`

Current remote HEAD: `14b183dedf8a55b12e9368229482ab4bdb3395b1`

R20R1R2 exact tested source: `81d989af438bdeda583a581f1ef7f311205e6139`

Immutable tested tag: `codex/r20r1r2-tested-source-20261003-r1`

Execution baseline: `0a6b8b0553ac9503b1d6a78681659b35c2ba934e`

---

# 1. Unique External Audit Decision

```text
R20R1R2_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED

P0_A_REAL_DM01_ACCEPTED_COMPONENT_LINEAGE = PASS
P0_B_NATIVE_DM01_FORWARD_PROJECTION = PASS

R20R1R2_REAL_DM01_DATA_HEAD_REACHABILITY = PASS
R20R1R2_REAL_DM01_ROW_SCHEMA_ADMISSION = PASS
PRODUCTION_SHAPED_POSITIVE_PATH = PASS_ENGINEERING
HORIZON_SCOPED_DEBT = PASS_KEEP

CURRENT_REAL_MATURITY_EVIDENCE = NONE
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

REALTIME_ACCEPTED_COHORT_MATURITY = NOT_GRANTED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_15_PROMOTION = AUTHORIZED
V4_15_ACCEPTED_HEAD = NOT_CREATED_YET
V4_16 = BLOCKED_UNTIL_V4_15_PROMOTION_EXTERNAL_VALIDATION
```

This is a final pass for the V4-15 runtime candidate within its explicitly capability-scoped boundary. It is not a claim that real T+1/T+3/T+5/T+10/T+20 outcomes already exist.

---

# 2. R20R1R2 P0-A｜PASS

The active resolver now traverses the actual production authority shape:

```text
V4_DATA_ACCEPTED_HEAD_V2
→ parent accepted Data Head / accepted batch anchor
→ DM01 accepted continuous chain
→ accepted candidate nodes
→ component receipts
→ native ADJUSTED_DAILY artifacts
```

The validator no longer depends on `FORWARD_EVALUATION_INPUTS` or an equivalent final-head shortcut.

The resolver checks exact V2 Data Head schema, frozen T0 ancestry, exact accepted-chain anchor, external acceptance record, candidate membership, accepted session continuity, candidate parent, parent component manifest, exact ADJUSTED_DAILY receipt, artifact/row digest, source revision, final component identity and final permission receipt. Production / Shadow / Focus remain false.

This closes the prior production-Data-Head-shape blocker.

---

# 3. R20R1R2 P0-B｜PASS

V4-15 settlement fields are now separated from native DM01 fields.

Native accepted rows remain in the producer schema, including:

```text
security_id
source_security_key
trade_date
open/high/low/close
source_authority
source_snapshot_id
source_digest
record_quality
identity_quality
identity_source_revision
price_basis
adjustment_readiness
adjustment_source_revision
qfq_mul
qfq_add
```

The new versioned projection:

```text
V4_15_ACCEPTED_FORWARD_EVALUATION_PROJECTION_V1
```

derives V4-15-specific fields separately and binds exact source evidence.

The projection verifies native source rows contain no fake settlement fields, TDX official source only, BaoStock OHLC substitution false, accepted adjustment readiness, exact raw→adjusted dependency, exact TDX delta with future rows consumed=0, accepted identity/adjustment revisions, due-date GBBQ/disposition authority, unsupported-action fail-closed behavior, exact T0 reference mapping, and exact source artifact/receipt/row-digest bindings.

This closes the prior native-row-schema blocker.

---

# 4. Actual Real T0 Admission｜PASS_CAPABILITY_SCOPED

`CURRENT_REAL_DM01_ADMISSION.json` is generated from the live accepted repository graph.

It reports:

```text
actual_native_row_admitted = true
T0 = 2026-09-30
native_price_basis = TDX_NATIVE_AFFINE_QFQ
adjustment_readiness = READY
native_T0_close = 2.52
frozen_T0_reference = 2.52
future_accepted_endpoint_count = 0
```

Therefore current real source compatibility at T0 is demonstrated while current future maturity remains correctly ungranted.

---

# 5. Production-Shaped Engineering Reachability｜PASS

The R2 fixture no longer uses the rejected `FORWARD_EVALUATION_INPUTS` model.

The final accepted-head shape contains the nine named production component slots, and the accepted batch chain carries daily candidate/component lineage.

Engineering transitions demonstrate:

```text
[]                     -> OPEN
[1]                    -> PARTIAL_MATURITY_EVIDENCE
[1,3]                  -> PARTIAL_MATURITY_EVIDENCE
[1,3,5,10,20]          -> FULL_REQUIRED_HORIZONS_PROVEN
```

The fixture remains explicitly:

```text
ISOLATED_ENGINEERING_REACHABILITY_ONLY
```

and cannot grant current real capability.

---

# 6. Append-Only Correction｜PASS

Same-cutoff correction handling requires explicit accepted-record binding of the prior revision.

Evidence demonstrates FIRST_OBSERVED immutability, LATEST_VALIDATED advancement, second-receipt append and rejection of unbound prior same-day snapshots.

---

# 7. Independent Oracle｜PASS

The R20R1R2 oracle independently traverses production-shaped accepted component lineage and recomputes accepted-session coverage, component membership, native source identity, accepted GBBQ bindings, affine coefficients, projection rows, transformed T0 reference, R_N, MFE_N, MAE_N, PATH_MDD_CLOSE_N and horizon coverage state.

It does not import the active resolver, projection writer, maturity debt writer, packet validator or V4-15 settlement evaluator to derive expected results.

---

# 8. Tested Source and Regression｜PASS

Immutable tested tag:

`codex/r20r1r2-tested-source-20261003-r1`

resolves to:

`81d989af438bdeda583a581f1ef7f311205e6139`

Current final HEAD is one evidence-only commit ahead.

Clean detached regression:

```text
R20 current       107
R20R1              51
R20R1R1            35
R20R1R2            38
---------------------
TOTAL              231 PASS

failed               0
errors               0
skipped              0
deselected           0
```

No implementation source changed after the tested source.

---

# 9. Protected State｜PASS

Still unchanged:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_15_ACCEPTED_HEAD =
NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false
```

R20 / R20R1 / R20R1R1 accepted successes are preserved.

---

# 10. Non-Blocking Test Enhancement

Carry as non-blocking validation debt:

```text
V4_15_FWD_ADJ_VECTOR_01 =
SUPPORTED_CORPORATE_ACTION_NON_IDENTITY_PROJECTION_VECTOR
```

The persisted R20R1R2 positive sequence is dominated by identity affine transforms. The accepted adjustment engine already has separate non-identity cash/bonus/rights reference tests, and V4-15 binds that implementation. Therefore this does not block Promotion.

A later regression should add at least one production-shaped path where a supported category-1 event occurs between T0 and due and:

```text
T0_transform_coefficients != {alpha:1,beta:0}
```

with independent numerical recomputation.

---

# 11. Promotion Boundary

V4-15 may now be promoted as:

```text
ENGINEERING_ACCEPTED_CAPABILITY_SCOPED
```

The Accepted Head must not claim real matured settlement, historical PIT, realtime cohort maturity, Production, Shadow or Focus.

Open validation debt remains non-blocking:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
```

with:

```text
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]
```

---

# 12. Final State

```text
R20R1R2_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED

V4_15_PROMOTION =
AUTHORIZED

NEXT =
R21_V4_15_ACCEPTED_HEAD_PROMOTION
```
