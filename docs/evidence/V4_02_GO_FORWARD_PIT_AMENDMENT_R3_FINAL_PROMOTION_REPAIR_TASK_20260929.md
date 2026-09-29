# V4-02 Go-Forward PIT Amendment R3
## Final Promotion Repair Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Starting HEAD:** `0f66e88052b33b90ab76ec39bfeb115386f8bca2`  
**Task Type:** Narrow final repair before external acceptance / promotion

---

# 0. Starting Status

R2 external audit:

`V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_BLOCKED_R2`

R2 data/source evidence already accepted:

```text
Official TDX package capture = PASS
Sep-28 package SHA = PASS
Sep-28 target-date contents = PASS
Sep-24 overlap = PASS
Frozen Sep-26 GBBQ identity = PASS
Sep-28 QFQ candidate = PASS
Determinism = PASS
No-backdating = PASS
Independent postcheck = PASS
```

Do not redo working parts unless required by schema/code changes.

---

# 1. Frozen Source Identities

Preserve exact official Sep-28 package:

```text
SHA256 =
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

bytes =
551001603
```

Preserve frozen adjustment source:

```text
snapshot =
sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e

gbbq =
f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1

gbbq.map =
f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8
```

Target:

`2026-09-28`

Historical AS_RECORDED remains blocked.

---

# 2. Repair U01 — New Listing / New Source Key

A target-date key may enter the required-board candidate only if all required conditions pass:

```text
official T0 raw bar exists
security type = A_STOCK
board in SH_MAIN / SZ_MAIN / CHINEXT / STAR
dated identity mapping resolves uniquely
list_date <= T0
delist_date >= T0 or null
symbol interval covers T0
no ambiguous security_id
```

For a valid newly listed security:

```text
include in target universe
include in adjusted candidate
preserve new-listing provenance
```

Do not require prior-cutoff membership.

If a target-date source key cannot be safely resolved:

`V4_02_GO_FORWARD_BLOCKED_UNIVERSE_IDENTITY`

Do not silently ignore it.

---

# 3. Mandatory New-Listing Tests

Add automated tests for:

- valid new listing included;
- unresolved new key blocks;
- future listing not eligible;
- ambiguous dated identity blocks.

The real Sep-28 case should remain unchanged if `new_source_keys=[]`.

---

# 4. Repair T01 — Publication-Time PIT Semantics

Do not write only:

`knowledge_lineage = PIT_OBSERVED`

for this delayed publication.

Freeze an explicit enum such as:

`PIT_OBSERVED_AFTER_FORMAL_PUBLICATION`

Every candidate row must include:

```text
target_trade_date
max_source_trade_date
official_raw_source_published_at
project_raw_source_available_at
adjustment_source_available_at
formal_publication_at
```

Required ordering:

```text
max_source_trade_date <= target_trade_date
adjustment_source_available_at <= formal_publication_at
project_raw_source_available_at <= formal_publication_at
formal_publication_at >= max(required source available_at)
```

Replay Gate A R2 must compare source availability to publication time.

---

# 5. Publication-Time Negative Tests

At minimum:

- delayed Sep-28 source captured Sep-29 and published Sep-29 = valid;
- publication before raw capture = hard fail;
- adjustment snapshot available after publication = hard fail;
- max_source_trade_date > target_trade_date = temporal leakage block.

---

# 6. Repair E01 — Bound Runtime Test Receipt

Create:

`reports/v4_02/V4_02_GO_FORWARD_R3_TEST_RECEIPT.json`

Bind:

```text
implementation_commit
exact test command
test file hashes
Python version
important dependency versions
started_at
finished_at
exit_code
passed
failed
skipped
```

Do not hardcode counts before execution.

Run:

```text
tests/v4_01
tests/v4_02
tests/v4_03
tests/v4_04
tests/v4_joint
tests/v4_phase0
```

plus new R3 go-forward tests.

---

# 7. Candidate-Specific Test Coverage

Add explicit tests for:

- Python HTML anti-bot response → curl fallback;
- valid ZIP target date;
- future raw row rejection;
- raw overlap mismatch blocking;
- valid new listing inclusion;
- unresolved new source key blocking;
- no-T0-bar fail-closed;
- supported category-1 QFQ;
- unsupported / unknown price event fail-closed;
- later non-price GBBQ revision does not alter T0 QFQ;
- later price-affecting event does not backdate;
- delayed formal-publication timestamps;
- deterministic output.

---

# 8. Repair R01 — Remote Git LFS Recoverability

Prove the remote object is recoverable independently from the current working-tree copy.

Use an isolated temporary clone/worktree or equivalent remote fetch.

Required semantics:

```text
obtain repository commit from origin
fetch LFS object from origin
materialize hsjday.zip
hash restored bytes
```

Required restored SHA256:

`70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c`

Create:

`reports/v4_02/V4_02_GO_FORWARD_REMOTE_LFS_RESTORE_R3.json`

If remote restore fails:

`V4_02_GO_FORWARD_BLOCKED_REMOTE_LFS_OBJECT_UNAVAILABLE`

---

# 9. Candidate Rebuild

Because lineage fields and universe implementation change, rebuild the Sep-28 candidate as:

`reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz`

Do not overwrite R2.

Record new:

```text
compressed SHA
logical digest
row counts
quality counts
board counts
```

Any unexpected row-count change requires an explicit diff receipt.

---

# 10. R2 → R3 Diff Receipt

Create:

`V4_02_GO_FORWARD_R2_R3_DIFF_R3.json`

Compare:

```text
security_id set
source_security_key set
raw OHLC
QFQ OHLC
quality
blocking event categories
visible event-set digest
lineage fields
```

Business price results should remain stable unless U01 exposes a real missed identity.

---

# 11. Independent R3 Postcheck

Independently verify:

- official package SHA;
- remote LFS restore SHA;
- target-date package integrity;
- universe/new-listing logic;
- frozen Sep-26 GBBQ identity;
- later snapshot not consumed;
- candidate row/security set;
- sample QFQ recomputation;
- unsupported-event fail closed;
- publication-time ordering;
- no-backdating;
- determinism;
- R2→R3 diff;
- accepted heads unchanged;
- TDX writes zero.

---

# 12. Accepted Heads

Do not modify:

```text
data/v4/V4_02_ACCEPTED_HEAD.json
data/v4/V4_04_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

Do not start V4-05 R2.

---

# 13. R3 Candidate Terminal Status

Only if all repairs pass:

`V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R3`

External acceptance remains:

`PENDING`

Historical AS_RECORDED remains:

`BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

---

# 14. Required Evidence Family

At minimum:

```text
reports/v4_02/V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R3.json
reports/v4_02/V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R3.json
reports/v4_02/V4_02_GO_FORWARD_DETERMINISM_R3.json
reports/v4_02/V4_02_GO_FORWARD_PUBLICATION_TIME_R3.json
reports/v4_02/V4_02_GO_FORWARD_REMOTE_LFS_RESTORE_R3.json
reports/v4_02/V4_02_GO_FORWARD_R3_TEST_RECEIPT.json
reports/v4_02/V4_02_GO_FORWARD_R2_R3_DIFF_R3.json
reports/v4_02/V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R3.json
reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_CANDIDATE_MANIFEST_R3.json
reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_CLOSURE_R3.md
```

---

# 15. Forbidden Work

Do not:

- overwrite R2 evidence;
- relabel historical AS_RECORDED;
- use BaoStock QFQ fallback;
- ignore a real new target-date listing;
- use a later GBBQ snapshot in T0 QFQ;
- modify V4-04 rules;
- start V4-05 R2;
- promote V4-02 / global Accepted Head;
- write into `D:/new_tdx`.

---

# 16. Stop Point

Stop after sealing R3 candidate.

Await independent external audit.

If R3 passes external audit, the next task card will authorize:

```text
V4-02 Go-Forward PIT Amendment Accepted Seal
+
V4-05 Replay Gate A R2
```
