# V4-02 Go-Forward PIT Adjustment Amendment Candidate R1 Task
## for V4-05 Replay Gate A Unblock

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Task Type:** Upstream go-forward PIT source/adjustment amendment candidate  
**Current HEAD baseline:** `52ff45b138fa536e802168a11aebbba6d1cb1d9d`

---

# 0. Governing Status

V4-04:

```text
FULL_PASS_REQUIRED_SCOPE
EXTERNALLY_ACCEPTED
```

V4-05 R1:

```text
V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

Accepted blocker:

```text
V4_05_BLOCKED_UPSTREAM_DEFECT_HISTORICAL_ADJUSTED_PRICE_PIT_LINEAGE
```

Historical AS_RECORDED adjusted prices currently remain:

```text
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

This task does **not** backfill or fabricate historical PIT.

Its purpose is to establish a separately versioned, real **go-forward PIT** source/adjustment capability that can later be consumed by V4-05 Replay Gate A R2.

---

# 1. Highest-Level Rule

Do not attempt to turn the existing historical artifact:

`V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet`

into a historical PIT artifact by relabeling it.

Do not infer:

```text
effective_date
=
first_available_date
```

Do not use a later GBBQ snapshot as if it were available at an earlier target date.

Do not overwrite V4-02 Accepted Head.

Do not change V4-04 Accepted Head.

Create a **new amendment candidate**.

---

# 2. Scope Split to Freeze

The new amendment must explicitly freeze two capabilities:

## 2.1 Historical AS_RECORDED

For dates before the go-forward snapshot system is formally available:

```text
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
=
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

Existing historical adjusted artifacts may remain:

```text
DIAGNOSTIC_NON_PIT
```

They may not be promoted to PIT evidence.

## 2.2 Go-Forward PIT

Candidate capability:

```text
GO_FORWARD_PIT_ADJUSTED_PRICE
```

This capability may only begin from an actual target publication whose required sources were frozen before or at that publication according to the source contract.

The existing forward snapshot receipt records:

```text
system_available_at =
2026-09-26T13:07:05Z

first_eligible_formal_trade_date =
2026-09-28
```

Therefore the first candidate target should be:

`2026-09-28`

provided all required source evidence can be independently established.

---

# 3. Do Not Use 2026-09-29 Incomplete Daily Data

At task issuance time, 2026-09-29 is not a completed A-share trading day.

Do not use an incomplete 2026-09-29 daily bar as the first formal go-forward publication.

Initial formal target:

`2026-09-28`

If local TDX does not contain a complete accepted 2026-09-28 close, issue an exact BLOCKED result rather than substituting the partial 2026-09-29 session.

---

# 4. Existing Frozen GBBQ Authority

Start from:

`reports/v4_02/V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_20260926.json`

Required identity:

```text
gbbq sha256 =
f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1

gbbq.map sha256 =
f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8
```

The manifest lineage permission must remain:

```text
PIT_OBSERVED_ELIGIBLE_FROM_FIRST_FORMAL_PUBLICATION_AFTER_SYSTEM_AVAILABLE_AT
```

This Sep-26 snapshot is the only adjustment/corporate-action evidence allowed to influence the initial Sep-28 T0 candidate unless another source was itself immutably frozen and provably available no later than that T0 publication.

---

# 5. Later GBBQ Snapshot Rule

A newer GBBQ snapshot may be captured after Sep-28 only for:

- revision diagnostics;
- completeness comparison;
- detecting records added/corrected after T0.

It may **not** rewrite the Sep-28 AS_RECORDED result.

If a later snapshot introduces or modifies a price-affecting record with:

```text
effective_date <= 2026-09-28
```

that was absent/different in the Sep-26 T0-visible snapshot, then affected Sep-28 securities must be marked with an explicit quality disposition, for example:

```text
PIT_SOURCE_REVISION_AFTER_T0
```

or:

```text
ADJUSTMENT_UNAVAILABLE_AT_T0
```

They may not be silently backfilled.

---

# 6. Required New Raw Daily Source Snapshot

The accepted V4-02 daily artifact stops at:

`2026-09-24`

Therefore Sep-28 go-forward PIT cannot be proven using the old accepted daily artifact alone.

Create an immutable **candidate source snapshot** from local TDX that includes the completed 2026-09-28 daily data.

Requirements:

- TDX root is read-only;
- copy into project-controlled staging/snapshot storage;
- hash every consumed file;
- record observed_at / system_available_at / ingested_at;
- record source cutoff;
- do not include partial Sep-29 rows in the Sep-28 publication;
- archive source identity atomically;
- produce overlap checks against the accepted Sep-24 chain.

At minimum compare the overlap period:

```text
2026-09-24
```

and preferably the most recent accepted overlapping sessions available in both revisions.

Any unexplained overlap mismatch must block the affected scope.

---

# 7. Incremental Universe / Identity Candidate

The accepted universe also stops at Sep-24.

For the Sep-28 candidate:

- preserve all previously accepted security IDs;
- apply existing dated alias/lifecycle contracts;
- test code changes;
- detect newly listed securities between Sep-25 and Sep-28;
- detect terminated/delisted membership changes if any;
- do not use future Sep-29 knowledge to alter Sep-28 membership.

Create a versioned candidate universe for Sep-28.

Do not overwrite:

`data/v4/V4_01_ACCEPTED_HEAD.json`

or existing accepted universe artifacts.

---

# 8. Go-Forward Adjustment Build

For target:

`T0 = 2026-09-28`

build QFQ/current-coordinate prices using only:

```text
raw bars available through T0
+
corporate-action records visible in the Sep-26 frozen GBBQ snapshot
+
effective_date <= T0
```

The historical lookback bars may be transformed into the T0 coordinate because that is a **current T0 computation**.

This is different from claiming those old dates had those adjustment facts available at their own historical timestamps.

Record this distinction explicitly:

```text
coordinate_basis =
T0_CURRENT_COORDINATE

historical_as_recorded_claim =
FALSE

source_visibility_basis =
GBBQ_SNAPSHOT_VISIBLE_BEFORE_T0
```

---

# 9. Adjustment Contract Requirements

Reuse the already accepted mathematical rules where applicable:

- affine factor semantics;
- cash dividend;
- share bonus / transfer;
- rights issue;
- combined action;
- missing-action fail closed;
- unsupported category fail closed;
- no BaoStock QFQ fallback.

Do not change formulas merely to match current outputs.

All price-affecting unsupported / ambiguous event categories must remain unavailable.

---

# 10. Real-Data Acceptance Samples

For the Sep-28 amendment candidate, include real samples covering as available:

- cash dividend;
- share bonus / transfer;
- rights issue;
- combined action;
- no-action control;
- suspension/resumption;
- recent listing;
- one code-change identity where relevant.

Each sample must bind:

```text
security_id
source_security_key
target_trade_date
raw source revision
GBBQ snapshot id
visible event set
effective event set
factor A/B
output QFQ
quality disposition
```

Do not reuse old diagnostic sample labels as proof of T0 visibility without rebinding them to the Sep-26 snapshot authority.

---

# 11. Full-Market Candidate Scope

If source availability permits, build a full required-board Sep-28 candidate:

- SH_MAIN
- SZ_MAIN
- CHINEXT
- STAR

BSE remains optional-degraded under existing policy.

For each security:

```text
RAW_READY
ADJUSTED_READY
ADJUSTED_UNAVAILABLE_<REASON>
```

must be explicit.

Do not remove securities merely because adjusted data is unavailable.

---

# 12. Required Lineage Fields

Every go-forward adjusted row must expose enough lineage to prove T0 visibility.

At minimum:

```text
target_trade_date
source_asof
system_available_at
raw_source_snapshot_id
raw_source_digest
adjustment_snapshot_id
adjustment_snapshot_digest
max_source_trade_date
knowledge_lineage
coordinate_basis
adjusted_quality
adjustment_reason
```

Required `knowledge_lineage` for accepted go-forward rows:

```text
PIT_OBSERVED
```

Historical rows in old artifacts remain:

```text
DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT
```

Do not overwrite history to change the label.

---

# 13. Determinism

Two builds from identical:

```text
raw snapshot
GBBQ snapshot
contract
parameter set
target date
identity map
```

must produce the same logical digest.

Record:

```text
first_run_digest
second_run_digest
same_logical_digest
```

Acceptance requires true.

---

# 14. No Backdating Test

Mandatory negative test:

Take an adjustment record that exists only in a later snapshot.

Attempt to replay Sep-28.

Expected:

```text
later-only record
MUST NOT influence Sep-28 output
```

If its absence makes a security's T0 adjustment unprovable:

```text
adjusted_quality = UNAVAILABLE
```

not retroactive correction.

---

# 15. Snapshot Revision Test

If a later GBBQ snapshot is available:

compare:

```text
Sep-26 frozen snapshot
vs later snapshot
```

classify:

- unchanged;
- future-effective addition;
- <=T0 late addition;
- <=T0 revision;
- deletion;
- unknown.

Only the Sep-26-visible event set may drive Sep-28 AS_RECORDED output.

Late <=T0 changes are audit evidence, not T0 input.

---

# 16. Output Family

Create versioned artifacts/receipts. Suggested names:

```text
reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_STAGE_ENTRY_R1.md

reports/v4_02/V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_R1.json

reports/v4_02/V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R1.json

reports/v4_02/V4_02_GO_FORWARD_GBBQ_VISIBILITY_R1.json

reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_CONTRACT_R1.json

reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R1.json

reports/v4_02/V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R1.json

reports/v4_02/V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R1.json

reports/v4_02/V4_02_GO_FORWARD_DETERMINISM_R1.json

reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_CANDIDATE_MANIFEST_R1.json
```

The exact names may follow repository conventions, but each evidence role must remain independently auditable.

---

# 17. Candidate Status

Allowed success status:

`V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R1`

This is **not** an accepted-head update.

It means only:

```text
a candidate go-forward PIT input chain
exists and is ready for external audit
```

Historical capability must still read:

```text
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE =
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

---

# 18. Failure Statuses

Use exact blockers.

Examples:

```text
V4_02_GO_FORWARD_BLOCKED_NO_COMPLETE_20260928_RAW

V4_02_GO_FORWARD_BLOCKED_SOURCE_OVERLAP_MISMATCH

V4_02_GO_FORWARD_BLOCKED_GBBQ_SNAPSHOT_IDENTITY

V4_02_GO_FORWARD_BLOCKED_ADJUSTMENT_REVISION_AFTER_T0

V4_02_GO_FORWARD_BLOCKED_IDENTITY_UNIVERSE

V4_02_GO_FORWARD_BLOCKED_NONDETERMINISTIC
```

Do not downgrade a real P0 to a generic warning.

---

# 19. Forbidden Work

Do not:

- overwrite V4-02 Accepted Head;
- overwrite V4-04 Accepted Head;
- change V4_STAGE_ACCEPTED_HEAD;
- relabel historical non-PIT rows as PIT;
- invent first-availability timestamps;
- use BaoStock adjusted OHLC as Core fallback;
- use Sep-29 incomplete bars as Sep-28 data;
- start V4-05 R2 replay in the same task;
- start V4-06;
- start V4-07;
- start V4-08;
- start PREWATCH;
- modify V4-04 algorithm thresholds;
- write into the user's TDX source root.

---

# 20. External-Audit Stop Point

This task stops after producing the go-forward PIT amendment **candidate**.

Do not promote it.

Do not rerun Replay Gate A R2 yet.

The next external audit must decide whether:

```text
GO_FORWARD_PIT_ADJUSTED_PRICE
```

is accepted.

Only after that external acceptance will a new task card authorize:

`V4-05 Replay Gate A R2`

with capability-scoped replay.

---

# 21. Required Closure Report

Record:

- starting HEAD;
- implementation commit;
- exact target date;
- TDX raw source snapshot identity;
- GBBQ snapshot identity;
- snapshot availability timestamp;
- overlap verification result;
- incremental universe result;
- adjustment contract digest;
- T0-visible event-set policy;
- full-market row/quality counts;
- deterministic build result;
- no-backdating result;
- later-snapshot revision audit if available;
- independent postcheck result;
- historical capability remains blocked;
- exact candidate terminal status.

Stop and await independent external acceptance.
