# V4-15E1 R1｜FEP Dataset & PostgreSQL Foundation Independent External Audit｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`ce44488ae972cf0f4d9f4af34cb03d81be436387`

Audited remote HEAD:

`e4ea913d8926e904e55cbf16993ec63c0e90b031`

Commit:

`Implement isolated FEP E1 PostgreSQL foundation and record blocked admission gates`

Task authority:

`V4_15E1_FEP_DATASET_AND_POSTGRESQL_FOUNDATION_IMPLEMENTATION_TASK_R1_20261005.md`

Frozen design:

```text
DA-MSR-V4.2.2-CODEX-REV4-FEP-R2
DA-MSR-V4.2.2-FEP-R2
FEP_SCHEMA_DESIGN_V2
```

---

# 1. Unique External Decision

```text
V4_15E1_R1_EXTERNAL_AUDIT =
PARTIAL_PASS_E1R1_REPAIR_REQUIRED

FEP_DATABASE_ENGINEERING =
PASS_KEEP_ISOLATED_POSTGRESQL

FEP_SCHEMA_33_TABLES =
PASS_KEEP

FEP_APPEND_ONLY_32_GUARDS =
PASS_KEEP

FEP_CONTROLLED_DEPLOYMENT_HEAD =
PASS_KEEP

FEP_ROLE_SECURITY =
PASS_KEEP

FEP_CAS_ENGINEERING =
PASS_KEEP

FEP_DATASET_TRANSACTION_ENGINEERING =
PASS_KEEP

FEP_FEATURE_REAL_OWNER_MAPPING =
FAIL_P0

FEP_V4_15_LABEL_THREE_TIME_AUTHORITY =
FAIL_P0

FEP_CROSS_STAGE_NAMESPACE_GOVERNANCE =
FAIL_P0

FEP_EXTERNAL_DESIGN_RAW_RECEIPT_BINDING =
FAIL_P1_EASY_REPAIR

V4_15E1_FEP_LOCAL_IMPLEMENTATION =
BLOCKED

E2_ENTRY =
NOT_AUTHORIZED

NEXT =
V4_15E1_R1_BLOCKER_REPAIR
```

This is **not** a request to redo E1 from scratch.

The PostgreSQL/database core is materially implemented and should be kept.

---

# 2. Scope / Commit Discipline｜PASS

The implementation is isolated under FEP-specific config, code, migration, tests and evidence.

No accepted Stage/Data/DM01 head was promoted or rewritten.

No model training, calibration, inference, MODEL_DISPLAY, PRIORITY_USE, production cutover or real Shadow was granted.

The implementation correctly self-reported:

```text
V4_15E1_FEP_LOCAL_IMPLEMENTATION = BLOCKED
```

rather than manufacturing an E1 PASS.

---

# 3. Migration Allocation｜PASS_KEEP

Codex did not assume migration `019`.

It independently scanned the repository and found existing V4 PostgreSQL migrations:

```text
001 ... 027
```

then allocated:

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

Existing migrations were not modified.

This follows the task requirement.

---

# 4. Real PostgreSQL Execution｜PASS_KEEP

Evidence reports:

```text
PostgreSQL 18.6
x86_64-windows
timezone = UTC
locale = C
data directory = E:/codex_tmp/...
isolated engineering fixtures only
no production credentials
```

Fresh and Upgrade paths were both exercised.

The implementation is not relying on SQLite, DuckDB or a parser-only claim.

---

# 5. Schema Inventory｜PASS_KEEP

R2 design requires:

```text
33 FEP tables
32 immutable fact/history tables
1 controlled mutable table = fep.deployment_heads
```

R1 implementation materially matches that structure.

The PostgreSQL migration creates the frozen table families including:

```text
contracts/scopes/field registry
observations/revisions
snapshots/feature values
label source bindings/revisions
datasets/denominator/fold cutoffs/fold selection/rows
training/model skeleton
permission/activation/deployment heads/receipts
prediction slots/runs/results
reports/priority projection
```

No evidence was found that a second parallel V4 publications system was created.

---

# 6. Append-Only Governance｜PASS_KEEP

The implementation retains the design invariant:

```text
all FEP fact/history tables
→ UPDATE/DELETE rejected

deployment_heads
→ controlled mutable CAS pointer
```

The explicit table inventory and guard evidence are materially present.

No “one-time pg_tables loop means future tables are protected forever” shortcut is used as the contract.

---

# 7. Role / SECURITY DEFINER Governance｜PASS_KEEP

The migration creates disjoint NOLOGIN roles:

```text
fep_schema_owner
fep_cas_owner
fep_application
fep_deployer
fep_adapter
fep_auditor
```

and denies PUBLIC access.

`fep.cas_deploy(...)` is owned by the dedicated CAS owner and the migration fixes function search paths.

The test-environment `fep_e1_admin` superuser is an isolated fixture administration role, not the application/deployer role installed as product authority.

No production privilege is granted.

---

# 8. CAS / Concurrency / Idempotency｜PASS_KEEP

Independent evidence shows, in both fresh and upgrade fixtures:

```text
concurrent initial CAS
→ exactly one PASS
→ exactly one FEP_CAS_CONFLICT

identical request replay
→ same version/readback

losing transaction
→ no partial accepted activation/receipt/head
```

The implementation also covers:

```text
changed args with same request_id
NULL parameter rejection
fake REVOKE
future-effective head misuse
PUBLIC execute denial
direct application DML denial
search_path hijack
```

This is sufficient to keep E1-A08/A09/A10 as PASS.

---

# 9. Dataset Mechanics｜PASS_KEEP

The engineering fixture correctly implements and tests:

```text
complete expected denominator
per-fold/per-partition cutoff
per-fold label revision selection
revision+digest binding
dataset row composite FK
PENDING/MISSING preservation
fold phase overlap guard
different-entity same local episode allowed
no-active-model slot retention
```

The required PIT counterfactual:

```text
early fold → r1
late fold → r2
early fold attempting r2 → BLOCK
```

is covered as an engineering fixture.

This portion should not be rewritten in the next repair.

---

# 10. Blocker P0-1｜Feature Owner Mapping Is Actually Incomplete

Current gate:

```text
accepted_registry_fields = 47
implemented_current_ENTRY_mappings = 0
FEP_E1_DATASET_COMPLETE = false
```

This is a real blocker.

The current `fep_feature_registry_v1.json` proves registry identity, type/unit intent and producer family, but does **not** prove the actual accepted 2026-09-30 row path / quality path / availability authority for the 47 required ENTRY fields.

Typical rows remain:

```text
field_path = null
quality_allowlist = []
status = NOT_IMPLEMENTED
```

The current discovery inspected a historical 2026-09-24 V4-04 profile sample and correctly refused to reuse it as proof for 2026-09-30.

That conservative decision is correct.

However, the repair must not assume all 47 values have to come from one V4-04 root row.

The 47 fields may legally be mapped to multiple accepted owners, for example:

```text
V4-03 accepted factor output
V4-04 profile derived_fields/states
V4-09 PREWATCH owner
V4-11 State/Event owner
V4-12 structure owner
V4-13 accepted advanced projection
```

provided every mapping exact-binds an accepted owner head/artifact/publication and a real value/quality path.

Therefore:

```text
FEP_E1_FEATURE_MAPPING_INCOMPLETE = VALID_BLOCKER
```

but the next task is an owner-mapping repair, not a schema redesign.

---

# 11. Blocker P0-2｜V4-15 Three-Time Label Authority Is Missing

FEP R2 requires three distinct times:

```text
source_fact_available_at
label_training_mature_at
label_revision_available_at
```

Current V4-15 outcome identity provides fields such as:

```text
report_cutoff
evaluation_revision
evaluation_source_digest
evidence_class
```

but does not provide an independently accepted authority for the three required timestamps.

Most importantly:

```text
report_cutoff
```

must not be silently reused as any/all three times.

Current V4-15 Accepted Head also says:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE
```

So the implementation is correct to keep the five current real rows nontrainable.

The repair must create a **versioned additive V4-15→FEP timing authority / sidecar contract**.

It must not rewrite old settlement rows and must not fabricate timestamps for current pending rows.

Therefore:

```text
FEP_E1_CONTRACT_CONFLICT_THREE_TIME_SOURCE = VALID_BLOCKER
```

---

# 12. Blocker P0-3｜V4-18 Namespace Inventory Conflict Is Real

The current V4-18 test does:

```text
scan all src/workbench_db/**/*.sql CREATE TABLE declarations
==
config/v4_18_migration_replay_contract_v1.json namespace_matrix
```

Adding 33 FEP tables therefore creates one genuinely new active regression:

```text
tests.test_v4_18_migration_contract::
test_all_declared_tables_have_explicit_namespace_rules
```

This is not a false positive.

But the correct repair is **not** to mutate the frozen V4-18 V1 contract in place.

V4-18 V1 predates FEP E1.

The correct action is:

```text
create versioned successor
V4_18_MIGRATION_REPLAY_CONTRACT_V1_1

bind V1 as immutable predecessor
add the 33 FEP declarations explicitly
keep migration execution / production cutover = NOT_GRANTED
update the active static test to the successor contract
```

FEP tables should enter the namespace matrix as explicit FEP-only engineering/reference scope; adding them must not grant migration/cutover authority.

Therefore:

```text
FEP_E1_CONTRACT_CONFLICT_V4_18_NAMESPACE_INVENTORY = VALID_BLOCKER
```

---

# 13. P1｜External Design Acceptance Raw Receipt Missing In Repository

Codex reported it could not locate the independently named external design acceptance original.

The authority does exist in the formal Drive archive.

Exact raw Drive file:

```text
V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md
bytes = 14019
sha256 =
cd279e26fb9753eb1e333c7554f9f06393c9232ee44ff7be6d86e2f2f65d178e
```

Drive ID:

```text
1SdxQCravi5BpyHQ7yb7_IanQpcI0wBW2
```

This is an easy governance repair:

```text
copy exact raw bytes into repo evidence
bind digest in DESIGN_AUTHORITY_READBACK / candidate seal
```

Do not rewrite or summarize the receipt.

---

# 14. Regression Classification｜Mostly Correct

Current scoped regression:

```text
passed = 2391
skipped = 3
current failures = 53
```

Classification:

```text
43 previously registered debts
9 failures reproduced on pre-FEP baseline in newly added scopes
1 genuinely introduced failure = V4-18 namespace inventory
```

The nine newly measured V4-15/publication failures are not automatically FEP-introduced merely because the old E1 regression did not include those scopes.

The separate baseline replay against the pre-FEP source/template is appropriate evidence that they pre-existed.

Therefore they remain owner-stage debt and do not require E1 to repair them in this round.

The one namespace failure **is** E1-introduced and must be closed before E1 can pass.

---

# 15. Additional Nonblocking Debt

Codex also found:

```text
FEP_E1_LEGACY_MIGRATION_REGISTRATION_GAP
```

because the historical migration service does not register all 014..027 migrations.

This is real legacy infrastructure debt, but the FEP E1 migration discovery and isolated bootstrap did not silently overwrite those migrations.

This issue remains:

```text
OPEN_EXISTING_INFRASTRUCTURE_DEBT
```

and is not promoted to a new E1 P0 in this audit.

Do not “fix” it inside the narrow E1R1 repair unless the change is separately scoped and independently justified.

---

# 16. What Must Be Preserved

Do not rewrite these PASS_KEEP areas:

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql

33-table identity
32 immutable guards
CAS semantics
role model
dataset denominator design
per-fold selection design
dataset composite FK
existing 40 negative vectors
```

A change is allowed only if the repair itself proves one of these bytes is objectively wrong.

Otherwise keep exact bytes and re-readback them.

---

# 17. Required Repair Scope

The next repair is limited to four work packages:

```text
WP-A
External design raw receipt formalization

WP-B
47-field accepted-owner mapping + current ENTRY source admission

WP-C
Versioned V4-15 → FEP three-time label authority

WP-D
Versioned V4-18 namespace successor reconciliation
```

Then run one integrated E1 re-audit candidate.

---

# 18. Exit Required From Repair

Only after all four packages close may Codex claim:

```text
V4_15E1_FEP_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_DATABASE_ENGINEERING =
PASS_LOCAL

FEP_DATASET_ENGINEERING =
PASS_LOCAL

FEP_STOCK_ENTRY_CORE_DATA_PATH =
ENGINEERING_READY

FEP_MODEL_ENGINEERING =
NOT_STARTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

NEXT =
STOP_WAIT_V4_15E1_INDEPENDENT_EXTERNAL_AUDIT
```

Until then:

```text
E2 = NOT_AUTHORIZED
```
