# V4-02 Go-Forward PIT Amendment R2 External Audit
## Official TDX Capture + Sep-28 Candidate Review

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Audit Date:** 2026-09-29  
**Reviewed HEAD:** `0f66e88052b33b90ab76ec39bfeb115386f8bca2`  
**Previous Baseline:** `1524dcad312652c28b1f03b558ec8b6a7a3d0aa9`

---

# 0. Final Disposition

R2 candidate terminal status produced by implementation:

`V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R2`

External audit result:

`V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_BLOCKED_R2`

Important distinction:

```text
R2 Sep-28 source package       = PASS
R2 Sep-28 raw overlap          = PASS
R2 Sep-28 adjustment candidate = PASS_AS_DATE_SCOPED_CANDIDATE
R2 determinism                 = PASS
R2 no-backdating               = PASS
R2 independent postcheck       = PASS

GO_FORWARD_PIT capability promotion = BLOCKED
```

The candidate is not rejected because the Sep-28 data is wrong.

It is blocked from formal capability promotion because four final governance/implementation defects remain:

1. future new-listing/new-source-key handling is not safe;
2. machine-readable PIT lineage is broader than the actual publication-time semantics;
3. test-run evidence is not independently bound;
4. Git LFS remote recoverability is not independently proven.

No Accepted Head should be updated yet.

---

# 1. Commit Chain Reviewed

```text
0f679b81133345c7778b0215e5dfdc52435af0c9
[V4-02] Build official Sep-28 go-forward PIT amendment candidate

e666b7632f5ef1564920a501a2f566422406bfd6
[V4-02] Audit later GBBQ revision without backdating T0

0f66e88052b33b90ab76ec39bfeb115386f8bca2
[V4-02] Seal go-forward PIT amendment candidate R2 for external audit
```

Accepted V4-02, V4-04 and global Accepted Heads remain unchanged.

**PASS**

---

# 2. Official TDX Auto-Download Repair

The original Python transfer failure is now correctly diagnosed.

Python attempts returned:

```text
HTTP 200
Content-Type = text/html
bytes = 986 / 987
ZIP = false
```

The independent Windows `curl.exe` fallback returned:

```text
HTTP 200
Content-Type = application/zip
Content-Length = 551001603
Last-Modified = Mon, 28 Sep 2026 07:58:05 GMT
```

Package:

```text
SHA256 =
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

bytes =
551001603
```

ZIP validation:

```text
entry_count = 12440
CRC = PASS
markets = BJ / SH / SZ
uncompressed_bytes = 952897792
```

The package is stored outside `D:/new_tdx`.

`tdx_root_write_count = 0`

**PASS**

---

# 3. Target-Date Package Semantics

Official metadata remained:

```text
HSJDAY_SOFT_TIME = 2026-09-28 15:58:05
```

Package max raw trade date:

`20260928`

Future raw row count:

`0`

Target-date bars:

```text
SH = 4865
SZ = 4503
BJ = 349
TOTAL = 9717
```

Therefore the downloaded package is a valid Sep-28 complete daily source package, not a later package truncated to Sep-28.

**PASS**

---

# 4. Raw Overlap with Accepted Sep-24 Chain

Accepted required-stock rows:

`5210`

Result:

```text
EXACT_OR_NORMALIZED_TOLERANCE_MATCH = 5210
ACCEPTED_ONLY = 0
MISMATCH = 0
PACKAGE_ONLY = 4129
```

No required-scope accepted row diverged.

**PASS**

---

# 5. Sep-28 Universe Candidate

R2 preserves:

`5222` accepted required-board identities.

Board counts:

```text
SH_MAIN  = 1702
SZ_MAIN  = 1494
CHINEXT  = 1408
STAR      = 618
```

Target actual bars:

`5210`

No target bar:

`12`

Actual R2 evidence:

```text
new_source_keys = []
unresolved_target_source_keys = []
unexplained_dropped_source_keys = []
```

The accepted code-change identity remains:

```text
300114 → 302132
security_id = SEC-EDEDE35FE66896ACCA0AC85EEB2F133B
```

For 2026-09-28 specifically, the universe result is internally consistent.

**PASS for Sep-28 candidate**

However, see blocker U01 below.

---

# 6. Frozen GBBQ Visibility

Pre-T0 adjustment source:

```text
snapshot =
sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e

system_available_at =
2026-09-26T13:07:05Z

gbbq SHA256 =
f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1

gbbq.map SHA256 =
f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8
```

Only the frozen Sep-26 event set with `effective_date <= 2026-09-28` is used for the T0 coordinate.

A later GBBQ snapshot is diagnostic-only.

**PASS**

---

# 7. Later GBBQ Revision Audit

Later-vs-frozen classification:

```text
UNCHANGED                 = 193349
LATE_LE_T0_ADDITION       = 21
LATE_LE_T0_REVISION       = 1
DELETION                  = 1
FUTURE_EFFECTIVE_ADDITION = 28
```

The <=T0 changed records are non-price-adjustment inputs under the frozen V4-02 classification.

Price-affecting / unknown-price-impact event set through T0 is unchanged.

Reported:

```text
price_affected_security_count = 0
later_records_used_for_t0_qfq = false
```

**PASS**

---

# 8. Sep-28 Adjusted Candidate

Candidate:

`reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R2.jsonl.gz`

SHA256:

`83d99b99603a77c24732d857fdffb44e8d20fa02e44a016c460137a5eac3eb7c`

Logical digest:

`920118935010f2b9e5de4b76b33b7537ffdadbd3cd91ae17fae368524caaebe6`

Rows:

`5222`

Quality:

```text
RAW_READY = 5210
ADJUSTED_READY = 5195
ADJUSTED_UNAVAILABLE_NO_T0_RAW = 12
ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT = 15
```

Unavailable securities remain in the universe.

No BaoStock QFQ fallback is used.

**PASS for Sep-28 date-scoped candidate**

---

# 9. Adjustment Semantics

R2 correctly freezes:

```text
coordinate_basis =
T0_CURRENT_COORDINATE

historical_as_recorded_claim =
false

source_visibility_basis =
FROZEN_PRE_T0_GBBQ_SNAPSHOT
```

Historical AS_RECORDED remains:

`BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

Real sample evidence covers cash dividend, share bonus / transfer, rights issue, combined action, no-action control, no-T0-bar, unsupported event and the accepted code-change identity.

**PASS**

---

# 10. Determinism

Two builds from identical inputs produced:

```text
same logical digest = true
same compressed SHA256 = true
```

**PASS**

---

# 11. No-Backdating

The negative test proves that a later-only <=T0 effective price event does not alter the frozen-source T0 result.

The actual later GBBQ snapshot was also compared and was not used for T0 QFQ.

**PASS**

---

# 12. Independent Postcheck

The independent postcheck verifies:

- official archive SHA;
- actual ZIP / CRC;
- Sep-28 SH/SZ bars;
- no future raw bars;
- raw overlap samples;
- four-board identity counts;
- frozen GBBQ hashes;
- later snapshot non-consumption;
- price-event-set equality;
- candidate hash/logical digest;
- quality counts;
- one nontrivial historical QFQ lookback recomputation;
- no-backdating;
- determinism;
- accepted heads unchanged;
- TDX writes = 0.

**PASS**

---

# 13. BLOCKER U01 — Future New-Listing Handling Is Not Safe

Current universe builder detects:

```python
new = sorted(target_bars - accepted.keys())
```

but final preserved scope is:

```python
preserved = sorted(set(accepted) & active_map.keys())
```

and the adjusted builder further restricts active identities to prior accepted keys.

Therefore, if a future target date contains a valid newly listed A-share that was not in the prior accepted cutoff universe, the code can detect it in `new_source_keys` but will not include it in the final adjusted candidate.

For Sep-28:

`new_source_keys = []`

so the current Sep-28 artifact is unaffected.

But the implementation is not safe enough to promote as a reusable go-forward capability.

**Blocking for capability promotion**

---

# 14. BLOCKER T01 — PIT Lineage Label Is Too Broad

The R2 contract says:

`PIT_OBSERVED_AFTER_FORMAL_PUBLICATION`

but candidate rows write:

`PIT_OBSERVED`

while also recording:

```text
target_trade_date = 20260928
system_available_at = 2026-09-29T06:53:52+00:00
```

This is acceptable for delayed post-market formal publication, but machine consumers must not mistake it for same-day/intraday availability.

Required repair: use an explicit lineage enum and explicit timestamps for source publication, project availability and formal publication.

**Blocking for capability promotion**

---

# 15. BLOCKER E01 — `52 focused tests passed` Is Not Independently Bound

The closure/manifest states:

`52 focused tests passed`

But there is:

- no R2 test receipt;
- no GitHub commit status;
- no GitHub Actions run;
- no candidate-specific R2 test file added under `tests/v4_02`.

The independent postcheck is useful and accepted, but the literal `52 passed` claim is not independently verified evidence.

**Blocking for promotion evidence**

---

# 16. BLOCKER R01 — Remote Git LFS Recoverability Is Not Independently Proven

The repository contains the expected Git LFS pointer:

```text
oid sha256:
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

size:
551001603
```

The local seal script proves the working machine had the object.

It does not prove that a fresh clone can retrieve the remote LFS object.

Because the raw source is authoritative for the candidate, repository recoverability must be proven before promotion.

**Blocking for promotion**

---

# 17. Non-Blocking Notes

- Sep-24 overlap depth is only one full cross-section date; this is acceptable for R2, though deeper overlap is useful later.
- Historical AS_RECORDED adjustment remains blocked and must not be relabeled.

---

# 18. Final External Decision

```text
V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_BLOCKED_R2
```

Accepted evidence:

```text
OFFICIAL_TDX_AUTO_DOWNLOAD = PASS
SEP28_RAW_PACKAGE = PASS
SEP28_RAW_OVERLAP = PASS
SEP28_UNIVERSE_ACTUAL_CASE = PASS
SEP28_GBBQ_VISIBILITY = PASS
SEP28_ADJUSTMENT_CANDIDATE = PASS
DETERMINISM = PASS
NO_BACKDATING = PASS
INDEPENDENT_POSTCHECK = PASS
```

Remaining blockers:

```text
U01 NEW_LISTING_FORWARD_HANDLING
T01 PUBLICATION_TIME_LINEAGE
E01 TEST_RUNTIME_RECEIPT
R01 REMOTE_LFS_RECOVERABILITY
```

---

# 19. Next Stage

Next task:

`V4_02_GO_FORWARD_PIT_AMENDMENT_R3_FINAL_PROMOTION_REPAIR`

Only after R3 external acceptance should a new task authorize:

```text
V4-02 go-forward amendment accepted seal
+
V4-05 Replay Gate A R2
```
