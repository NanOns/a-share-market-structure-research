# V4-08 R4｜Input Promotion + First PIT Materialization + NOT_APPLICABLE AST Repair

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Required Starting HEAD:** `097a22f3fd8f7be405eab6e64a4f513d2ec64413`  
**Task Date:** 2026-09-30

---

# 0. External R3 disposition

Authority:

`V4_08_R3_INDEPENDENT_EXTERNAL_AUDIT_20260930`

R3 external state:

```text
V4_08_R3_EXTERNAL_ACCEPTANCE_BLOCKED_INPUT_PROMOTION_AUTHORIZED
```

Closed / accepted:

```text
B01-B05
B06 target-day lifecycle closure
B07 source/snapshot/fact basis guard
B08 disposable clean regression
source-time policy
calendar engineering extension
identity engineering increment
R1A/R1B/R2/R3 vector coverage
```

Do not redo those items unless regression proves a new defect.

---

# 1. Exact external promotion authorization

## 1.1 Identity

Authorized candidate:

```text
data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json

sha256 =
9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c
```

Identity artifact:

```text
data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json

sha256 =
98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603
```

External acceptance scope:

```text
2026-09-30 TARGET-DAY INCREMENTAL IDENTITY CLOSURE
```

No broader whole-market lifecycle-completeness claim.

## 1.2 Calendar

Authorized candidate:

```text
data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json

sha256 =
800a32d26b8a6089f67eda77e84c2364d4d0fd8a9879ed1b5c620be71202631b
```

Calendar artifact:

```text
data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json

sha256 =
abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3
```

External acceptance scope:

```text
SSE/SZSE MARKET SESSIONS THROUGH 2026-09-30
```

If any bound digest differs: STOP.

---

# 2. Workstream A｜Promote V4-01 identity input

Do not mutate the candidate artifact.

Create append-only promotion output, suggested:

```text
data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json
reports/v4_01/V4_01_GO_FORWARD_IDENTITY_EXTERNAL_PROMOTION_R1.json
```

Because the current candidate lifecycle records still carry:

```text
acceptance =
CANDIDATE_PENDING_EXTERNAL_PROMOTION
```

the formal runtime cannot merely point an accepted head at the unchanged candidate records if it requires:

```text
identity.acceptance == ACCEPTED
```

Use one of these formally frozen approaches:

### Preferred

Create a new immutable accepted identity artifact:

```text
security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json
```

derived deterministically from the candidate artifact.

Allowed semantic changes:

```text
only promotion metadata / acceptance state
```

For the two new target-active records:

```text
SZ.001246
SZ.301716
```

promote:

```text
CANDIDATE_PENDING_EXTERNAL_PROMOTION
→ ACCEPTED
```

Must NOT change:

```text
security_id
source_security_key
exchange
board
list_date
symbol_effective_from
source evidence
observed_at
```

All parent R7 records must remain exact.

The 9 `NOT_LISTED_AT_TARGET` dispositions are not turned into accepted active security records.

---

# 3. Identity promotion independent postcheck

Required checks:

```text
candidate digest exact
candidate artifact unchanged
parent R7 unchanged
new active count = 2
accepted target-active additions = exactly {SZ.001246, SZ.301716}
security_id unchanged
list_date unchanged
board unchanged
source evidence unchanged
no third new active security
unresolved target-day required key count = 0
```

Persist logical diff.

---

# 4. Workstream B｜Promote V4-02 calendar extension

Create append-only promotion head, suggested:

```text
data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json
reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_EXTERNAL_PROMOTION_R1.json
```

The accepted extension must reference the exact already-audited artifact.

No calendar recomputation is necessary unless required for independent readback.

Exact sessions:

```text
SSE:
2026-09-28 session 787
2026-09-29 session 788
2026-09-30 session 789

SZSE:
2026-09-28 session 787
2026-09-29 session 788
2026-09-30 session 789
```

Parent accepted calendars through 2026-09-24 remain immutable.

---

# 5. Calendar promotion postcheck

Required:

```text
parent digest unchanged
candidate extension digest exact
9/25-9/27 not sessions
9/28-9/30 sessions
SSE/SZSE dates identical
session sequence contiguous from 786
no stock bars used to invent sessions
accepted coverage end = 2026-09-30
```

---

# 6. Workstream C｜Materialize first real PIT membership candidate

After A and B promotions are present:

```text
target_trade_date =
2026-09-30
```

Bind:

```text
accepted go-forward identity head
accepted go-forward calendar head
V4_08_TDX_SOURCE_AVAILABILITY_POLICY_V2
migration 019 basis guard
R3 frozen exact-day TDX source bytes
sector-type registry
```

Source capture exact hash set is inherited from R3.

Do not recapture unless a source correction is intentionally introduced as a new revision.

---

# 7. Source revision

Create actual append-only PIT source revision with:

```text
membership_basis =
PIT_OBSERVED

revision_quality =
PIT_OBSERVED_ACCEPTED

provider_available_at_basis =
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES

membership_asof_basis =
PROJECT_FIRST_OBSERVED_SOURCE_STATE

membership_asof_date =
2026-09-30
```

Bind:

```text
source_bytes_digest
temporal_evidence_digest
source_file_digests
observed_at
system_available_at
revision chain
supersedes revision if applicable
```

No existing revision UPDATE.

---

# 8. Snapshot

Create actual snapshot:

```text
membership_basis =
PIT_OBSERVED

membership_quality =
PIT_OBSERVED_ACCEPTED

pit_observed =
true

historical_backtest_safe =
true

target_trade_date =
2026-09-30
```

No mixed raw/derived-parent lineage.

Formal PIT snapshot contains only accepted raw provider membership facts.

Derived-parent remains separate diagnostic lineage.

---

# 9. Active-universe admission

Formal member facts require accepted target-day identity.

Allowed required boards:

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR
```

BSE remains optional/degraded.

Exclude:

```text
NOT_LISTED_AT_TARGET
NON_EQUITY
OPTIONAL_BOARD
UNMAPPED
DELISTED_AT_TARGET
IDENTITY_UNAVAILABLE_AT_CUTOFF
```

Preserve excluded source rows in diagnostics.

---

# 10. Sector types

Formal membership:

```text
INDUSTRY
THEME
```

Exclude formal qualification:

```text
STYLE
UNKNOWN
DERIVED_PARENT
```

Do not silently delete diagnostic rows.

---

# 11. Expected full-row relationship

R3 prospectively computed:

```text
INDUSTRY = 5224
THEME = 44938
```

These are NOT oracle constants.

R4 must independently recompute.

If exact counts differ:

- do not force them;
- explain every difference;
- bind new source revision if source bytes changed;
- fail if unexplained.

---

# 12. Formal PostgreSQL readback

Using migrations through 019, prove actual accepted PIT facts are visible through:

```text
v4.formal_sector_membership
```

Required:

```text
source revision basis = PIT_OBSERVED
snapshot basis = PIT_OBSERVED
fact basis = PIT_OBSERVED
all three quality = accepted
mapped identity
history-safe = true
exact asof
valid source revision chain
provider/system availability <= cutoff
```

Negative rows must remain excluded.

---

# 13. Independent membership verifier

Independent verifier must NOT reuse producer admission result as oracle.

Recompute from:

```text
raw frozen source rows
accepted identity artifact
accepted calendar extension
sector-type registry
source-time policy
```

Compare:

```text
member identity set
sector identity set
INDUSTRY row set
THEME row set
exclusion reasons
logical digest
```

---

# 14. PIT determinism

Run exact materialization twice from immutable inputs.

Expected:

```text
same logical snapshot id
same source revision identity
same fact logical digest
same INDUSTRY set
same THEME set
same exclusion inventory
```

Exclude only non-logical timestamps from digest where contract says so.

---

# 15. No history backfill

Before first accepted snapshot:

```text
CURRENT_MEMBERSHIP_REPLAY
DIAGNOSTIC_ONLY
```

Do not convert historical replay into PIT_OBSERVED.

No 2026-09-28 or 2026-09-29 PIT reconstruction from the 9/30 bytes.

---

# 16. Workstream D｜Fix canonical AST NOT_APPLICABLE

Current R3 canonical evaluator only supports:

```text
TRUE
FALSE
UNKNOWN
```

This is insufficient.

Add explicit value:

```text
NOT_APPLICABLE
```

Canonical AST evaluation must preserve REV2 semantics.

---

# 17. Required four-state logic

At minimum implement and test:

```text
TRUE
FALSE
UNKNOWN
NOT_APPLICABLE
```

For branch-composition rules, distinguish:

- logical unknown;
- branch unavailable / not applicable.

Do not collapse N/A into FALSE.

---

# 18. Required mature retention behavior

Exact invariant:

```text
strong_prev = 0
→ strong_member_retention_1 = NOT_APPLICABLE
→ mature_retained = NOT_APPLICABLE
```

This:

- does NOT block ROTATION_IN;
- does NOT block ROTATION_ACCEPTED;
- cannot itself qualify ROTATION_EXPANDING;
- cannot itself qualify ROTATION_REACCELERATING;
- must not produce reason `MATURE_RETENTION_FAILED`.

---

# 19. Required early OR behavior

REV2 behavior for:

```text
base_seed_retention branch
OR
breadth_retention branch
```

must be explicitly encoded.

Required vectors include:

```text
TRUE OR N/A = TRUE

N/A OR TRUE = TRUE

FALSE OR N/A =
branch semantics explicitly frozen

N/A OR N/A =
UNKNOWN / NO_USABLE_RETENTION_BRANCH
per governing contract
```

Do not guess; bind exact REV2 interpretation in machine contract.

---

# 20. AST evidence

Produce:

```text
V4_08_R4_AST_NOT_APPLICABLE_ACCEPTANCE.json
V4_08_R4_AST_FOUR_STATE_TRUTH_TABLE.json
V4_08_R4_ROTATION_VECTOR_COVERAGE.json
```

Must exercise canonical `machine_ast` evaluator, not only legacy `evaluate_rotation_vector()` helper.

---

# 21. Five retention parameters remain pending

Do not assign values unless separately authorized.

Keep:

```text
V4_08_EARLY_SEED_RETENTION_MIN
V4_08_EARLY_BREADTH_RETENTION_MIN
V4_08_EARLY_BREADTH_DELTA_MIN
V4_08_EARLY_TOP1_CONCENTRATION_MAX
V4_08_MATURE_STRONG_RETENTION_MIN
```

as null if no approved decision exists.

This does not block PIT membership acceptance.

It continues to block affected Rotation formal consumer.

---

# 22. Prior-RPS / B2 / V4-10

Keep statuses truthful:

```text
Prior-RPS = OPEN
B2 Legacy Adapter = NOT_IMPLEMENTED
V4-10 production reducer/FSM = NOT_IMPLEMENTED
```

Do not solve them by placeholder defaults.

They are separate from membership acceptance.

---

# 23. Clean checkout

After implementation commit:

- clean detached checkout;
- disposable PostgreSQL only;
- no copied `.env`;
- process-scoped DSN;
- migrations 001–019;
- required regression families;
- git clean before/after;
- destroy cluster.

Do not hardcode test count.

---

# 24. Mandatory R4 evidence

At minimum:

```text
reports/v4_01/
V4_01_GO_FORWARD_IDENTITY_EXTERNAL_PROMOTION_R1.json
V4_01_GO_FORWARD_IDENTITY_PROMOTION_POSTCHECK_R1.json

reports/v4_02/
V4_02_GO_FORWARD_CALENDAR_EXTENSION_EXTERNAL_PROMOTION_R1.json
V4_02_GO_FORWARD_CALENDAR_EXTENSION_PROMOTION_POSTCHECK_R1.json

reports/v4_08/
V4_08_R4_STAGE_ENTRY.md
V4_08_R4_PIT_SOURCE_REVISION.json
V4_08_R4_PIT_SNAPSHOT.json
V4_08_R4_PIT_FACT_COUNTS.json
V4_08_R4_PIT_EXCLUSION_INVENTORY.json
V4_08_R4_PIT_FORMAL_VIEW_READBACK.json
V4_08_R4_PIT_INDEPENDENT_POSTCHECK.json
V4_08_R4_PIT_DETERMINISM.json
V4_08_R4_PIT_TEMPORAL_LEAKAGE.json

V4_08_R4_AST_NOT_APPLICABLE_ACCEPTANCE.json
V4_08_R4_AST_FOUR_STATE_TRUTH_TABLE.json
V4_08_R4_ROTATION_VECTOR_COVERAGE.json

V4_08_R4_SCHEMA_MIGRATION_RECEIPT.json
V4_08_R4_ISOLATED_REGRESSION.json
V4_08_R4_CLEAN_CHECKOUT_RECEIPT.json
V4_08_R4_STAGE_CANDIDATE_MANIFEST.json
V4_08_R4_CLOSURE.md
V4_08_R4_EXTERNAL_REAUDIT_HANDOFF.json
```

---

# 25. Accepted-head governance

R4 may create promoted accepted input heads for V4-01/V4-02 because this R3 external audit explicitly authorizes them.

R4 must **not** self-create final:

```text
V4_08_ACCEPTED_HEAD
```

unless existing governance explicitly permits a candidate head distinct from external acceptance.

Preferred:

```text
V4_08_PIT_MEMBERSHIP_CANDIDATE_HEAD_R1
```

then stop for final external audit.

---

# 26. R4 terminal

If actual PIT baseline is materialized and all membership checks pass:

```text
V4_08_R4_PIT_MEMBERSHIP_CANDIDATE_READY_FOR_FINAL_EXTERNAL_ACCEPTANCE
```

If AST N/A repair also passes:

```text
ROTATION_AST_ENGINEERING_R4_PASS
```

Five retention params can remain pending and formal Rotation consumer disabled.

If anything fails:

```text
V4_08_R4_BLOCKED_<EXACT_SCOPE>
```

No vague `BLOCKED`.

---

# 27. Final handoff

Report exact:

- pushed HEAD;
- commit list;
- identity promotion head + artifact digest;
- calendar promotion head + artifact digest;
- source revision id/digests;
- snapshot id/digest;
- INDUSTRY/THEME actual counts;
- unique sector/member counts;
- exclusion inventory;
- formal-view row count;
- independent verifier digest;
- determinism digests;
- four-state AST truth table;
- strong_prev=0 mature N/A vector;
- regression summary;
- disposable DB identity;
- five pending parameter ids;
- Prior-RPS status;
- B2/V4-10 status;
- no final V4-08 Accepted Head assertion.

Then stop for final independent acceptance.
