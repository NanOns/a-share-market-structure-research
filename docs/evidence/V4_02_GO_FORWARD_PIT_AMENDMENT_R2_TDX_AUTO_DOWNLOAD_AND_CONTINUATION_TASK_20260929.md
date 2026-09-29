# V4-02 Go-Forward PIT Amendment R2
## Official TDX Auto-Download Repair + Candidate Continuation Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Starting HEAD:** `1524dcad312652c28b1f03b558ec8b6a7a3d0aa9`  
**Task Type:** Official raw-source capture repair + go-forward PIT amendment candidate continuation

---

# 0. Authority

Governing documents:

- `AGENTS.md`
- `A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`
- V4-04 Accepted Head
- V4-05 R1 blocker evidence
- `V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R1_TASK_20260929.md`
- `V4_02_GO_FORWARD_PIT_AMENDMENT_R1_EXTERNAL_AUDIT_20260929.md`

Current upstream status:

```text
V4-04 = EXTERNALLY_ACCEPTED
V4-05 = BLOCKED_R1
historical AS_RECORDED adjustment = BLOCKED
go-forward PIT adjustment = NOT_ACCEPTED
```

---

# 1. New Frozen Environment Fact

Do not expect the user's local TDX installation to supply Sep-28 data.

Freeze:

```text
LOCAL_TDX_USABLE_CUTOFF = 2026-09-24
```

`D:/new_tdx` is read-only.

No user manual download is required for this task.

If a complete Sep-28 package is required, Codex is explicitly authorized to download it itself from the approved official TDX public source into **project-controlled storage**.

---

# 2. Approved Official Source

Primary page:

`https://www.tdx.com.cn/article/vipdata.html`

Page-discovered full daily package:

`https://data.tdx.com.cn/vipdoc/hsjday.zip`

Official update metadata:

`https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js`

Allowed hosts:

```text
www.tdx.com.cn
data.tdx.com.cn
```

Do not use third-party mirrors as the authoritative source.

---

# 3. Immediate Target Rule

Preferred target:

`T0 = 2026-09-28`

The already captured official metadata reports:

```text
HSJDAY_SOFT_TIME = 2026-09-28 15:58:05
HSJDAY_SOFT_SIZE = 525.47MB
```

Before downloading, fetch fresh update metadata again.

## Case A — metadata is still Sep-28

Download and freeze immediately under Sep-28.

## Case B — metadata has rolled beyond Sep-28 before any valid Sep-28 archive was frozen

Do **not** label the current archive as Sep-28.

Emit:

`V4_02_GO_FORWARD_BLOCKED_20260928_OFFICIAL_PACKAGE_ROLLED_FORWARD`

and preserve:

- prior Sep-28 page/update-info capture;
- fresh current metadata;
- exact rollover time;
- current package date.

Then determine the next target only under a separately provable forward-source chain.

Do not fabricate Sep-28 raw provenance by truncating a later snapshot.

---

# 4. Repair the Downloader Before Retrying

Modify the official downloader so every attempt records diagnostic evidence even when the archive is invalid.

Required per attempt:

```text
attempt_id
method
started_at
finished_at
elapsed_seconds
requested_url
final_url
HTTP status
Content-Type
Content-Length
ETag
Last-Modified
Content-Disposition
actual_byte_count
sha256_if_complete
first_64_bytes_hex
last_128_bytes_hex
zip_magic_check
zip_is_zipfile
failure_reason
```

For invalid non-ZIP payloads, persist only a **bounded diagnostic prefix/suffix** and HTTP metadata.

Do not retain an unbounded 500MB invalid payload unless needed for a valid retry/resume and safely quarantined.

---

# 5. Official Download Retry Policy

A single `urllib` failure is not terminal.

Implement a bounded retry policy.

At minimum attempt:

## Method A — Python HTTP client

Use:

- official URL only;
- redirects only inside official allowlist;
- browser-compatible User-Agent;
- `Referer: https://www.tdx.com.cn/article/vipdata.html`;
- long transfer timeout appropriate for ~525MB;
- retries with bounded exponential backoff;
- streamed SHA256;
- content-length validation when present.

## Method B — OS transfer client

If Method A does not produce a valid ZIP, use an independent OS-level official transfer path.

On Windows prefer one of:

```text
curl.exe
PowerShell Invoke-WebRequest
BITS transfer
```

Still use only the same official URL.

Record the exact command/method and resulting SHA.

Example semantics for `curl.exe`:

```text
--location
--fail
--retry 5
--retry-all-errors
--connect-timeout 30
long total transfer timeout
official Referer
browser-like User-Agent
```

Do not require user interaction.

---

# 6. Transfer Completion Rules

Never validate a partially written file.

Use:

```text
*.part
```

or an equivalent temporary path.

Only after:

```text
transfer complete
+
expected Content-Length satisfied when provided
+
ZIP validation PASS
+
SHA256 finalized
```

atomically move to immutable snapshot storage.

---

# 7. ZIP Validation R2

Require:

```text
magic / is_zipfile
central-directory readable
entry-count bound
uncompressed-size bound
per-entry size bound
compression-ratio bound
CRC PASS
no absolute path
no drive path
no ..
no symlink
no case-insensitive duplicate path
```

Normalize both:

```text
/
\
```

Path-layout validation must recognize safe official market hierarchies even if the ZIP has an optional single wrapper directory.

Require SH and SZ `.day` data.

BJ remains optional-degraded under the existing policy.

---

# 8. Immutable Project Snapshot

A successful package must be stored outside the TDX root, for example:

```text
data/v4/source_snapshots/tdx/20260928/
  sha256-<PACKAGE_SHA>/
    hsjday.zip
    page.html
    update_info.js
    capture_receipt.json
    package_manifest.json
```

Never extract over:

`D:/new_tdx`

Never mutate:

`D:/new_tdx`

Required:

`tdx_root_write_count = 0`

---

# 9. Extract Into Project-Controlled Staging

Extract only after ZIP validation into a project-owned immutable/staging location.

Example:

```text
data/v4/source_snapshot_store/tdx_daily/
  sha256-<PACKAGE_SHA>/
```

Record:

- package SHA;
- extraction manifest;
- file count;
- content digest;
- SH/SZ/BJ inventory;
- `.day` structural validity;
- target-date max date.

---

# 10. Target-Date Content Check

For a Sep-28 package require:

```text
max raw trade date = 20260928
```

for the package publication scope.

Do not require every security file to end on Sep-28 because suspension/delisting/new listing can legitimately differ.

But prove broad target-date content exists for both SH and SZ.

Record:

```text
sh_files_with_20260928_bar
sz_files_with_20260928_bar
bj_files_with_20260928_bar
target_date_total_bars
future_date_bar_count
```

For a Sep-28 PIT snapshot:

```text
future_date_bar_count must be 0
```

---

# 11. Accepted-Chain Overlap Verification

Compare the newly captured official raw package against the accepted pre-existing raw chain for overlapping dates.

At minimum include:

`2026-09-24`

Prefer the most recent 20–60 overlapping sessions if runtime permits.

Compare raw:

```text
security identity
trade_date
open
high
low
close
volume
amount
```

Do not compare adjusted QFQ as a raw-source identity test.

Classify:

```text
EXACT_MATCH
NORMALIZED_TOLERANCE_MATCH
PACKAGE_ONLY
ACCEPTED_ONLY
MISMATCH
```

Unexplained required-scope raw mismatches block the candidate.

---

# 12. Incremental Universe / Identity Through T0

Build a versioned Sep-28 universe/identity **candidate**, not an Accepted Head overwrite.

Requirements:

- retain accepted security IDs;
- apply dated alias/lifecycle rules;
- include valid newly listed securities through Sep-28;
- handle `300114 → 302132` identity with existing accepted lifecycle semantics;
- do not use Sep-29+ knowledge;
- record membership/source basis.

If the source package includes non-equity objects, do not expand the stock research universe merely because they are present in the ZIP.

---

# 13. GBBQ Source Visibility

Use the already frozen Sep-26 GBBQ snapshot:

```text
snapshot_id =
sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e

system_available_at =
2026-09-26T13:07:05Z
```

Verify:

```text
gbbq SHA =
f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1

gbbq.map SHA =
f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8
```

Only records visible in this frozen snapshot may affect Sep-28 AS_RECORDED adjustment.

Historical first-availability before the snapshot remains unclaimed.

---

# 14. Go-Forward QFQ Semantics

For T0 Sep-28, it is valid to transform historical raw lookback bars into the **Sep-28 current coordinate** using corporate-action facts visible before the Sep-28 formal publication.

Freeze:

```text
coordinate_basis =
T0_CURRENT_COORDINATE

historical_as_recorded_claim =
FALSE

source_visibility_basis =
FROZEN_PRE_T0_GBBQ_SNAPSHOT

knowledge_lineage =
PIT_OBSERVED
```

Do not reinterpret historical bar dates as having known the later adjustment event at their own original dates.

---

# 15. Fail-Closed Adjustment Rules

Reuse accepted adjustment math.

If the frozen Sep-26 GBBQ evidence is insufficient for a security:

```text
adjusted_quality = UNAVAILABLE
```

with a reason.

Do not:

- silently fall back to raw for adjusted indicators;
- use BaoStock QFQ as Core fallback;
- pull a later action snapshot and retroactively insert it into Sep-28.

---

# 16. Full Required-Board T0 Candidate

Build full required stock scope:

- SH_MAIN
- SZ_MAIN
- CHINEXT
- STAR

Record counts:

```text
RAW_READY
ADJUSTED_READY
ADJUSTED_UNAVAILABLE_*
```

Keep securities in the universe even when adjusted values fail closed.

BSE remains optional-degraded.

---

# 17. Later-Snapshot No-Backdating Test

If a later GBBQ snapshot exists or can be safely frozen after T0, use it only for diagnostic comparison.

Classify records:

```text
UNCHANGED
FUTURE_EFFECTIVE_ADDITION
LATE_<=T0_ADDITION
LATE_<=T0_REVISION
DELETION
UNKNOWN
```

Any later-only <=T0 record must not alter the frozen Sep-28 output.

If it proves the Sep-28 event set incomplete:

```text
mark affected T0 quality
do not rewrite T0 as if the record was known
```

---

# 18. Determinism

Run the full candidate twice from identical:

```text
raw package SHA
extraction manifest
GBBQ snapshot SHA
identity/universe candidate
contract
parameters
T0
```

Require identical logical digest.

---

# 19. Independent Postcheck

Create an independent verifier that does not trust the production builder's PASS result.

It must independently check:

- package SHA;
- ZIP validity;
- target-date max date;
- no future raw row;
- overlap sample;
- required-board universe coverage;
- GBBQ identity;
- visible-event cutoff;
- sample QFQ recomputation;
- fail-closed counts;
- deterministic digest;
- accepted heads unchanged;
- TDX root write count zero.

---

# 20. Required R2 Evidence Family

At minimum create:

```text
reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json
reports/v4_02/V4_02_GO_FORWARD_TDX_PACKAGE_RECEIPT_R2.json
reports/v4_02/V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_R2.json
reports/v4_02/V4_02_GO_FORWARD_RAW_OVERLAP_R2.json
reports/v4_02/V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R2.json
reports/v4_02/V4_02_GO_FORWARD_GBBQ_VISIBILITY_R2.json
reports/v4_02/V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R2.json
reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R2.json
reports/v4_02/V4_02_GO_FORWARD_NO_BACKDATING_R2.json
reports/v4_02/V4_02_GO_FORWARD_DETERMINISM_R2.json
reports/v4_02/V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R2.json
reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_CANDIDATE_MANIFEST_R2.json
```

Names may differ slightly under repository conventions, but all evidence roles must remain independently identifiable.

---

# 21. Success Status

Only after every required source/adjustment gate passes may the stage declare:

`V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R2`

This is a **candidate** only.

Do not update V4-02 Accepted Head.

Do not update V4-04 Accepted Head.

Do not update the global Accepted Head.

Do not start V4-05 R2 in this task.

Stop for external audit.

---

# 22. Failure Statuses

Use exact statuses.

Examples:

```text
V4_02_GO_FORWARD_BLOCKED_OFFICIAL_DOWNLOAD_ENVIRONMENT

V4_02_GO_FORWARD_BLOCKED_20260928_OFFICIAL_PACKAGE_ROLLED_FORWARD

V4_02_GO_FORWARD_BLOCKED_INVALID_OFFICIAL_ZIP

V4_02_GO_FORWARD_BLOCKED_RAW_OVERLAP_MISMATCH

V4_02_GO_FORWARD_BLOCKED_TARGET_DATE_CONTENT

V4_02_GO_FORWARD_BLOCKED_UNIVERSE_IDENTITY

V4_02_GO_FORWARD_BLOCKED_ADJUSTMENT_VISIBILITY

V4_02_GO_FORWARD_BLOCKED_NONDETERMINISTIC
```

A failed Python client alone is not sufficient for `OFFICIAL_DOWNLOAD_ENVIRONMENT` until the independent official transfer path has also failed and its diagnostics are recorded.

---

# 23. Forbidden Work

Do not:

- ask the user to manually download the Sep-28 package;
- write into `D:/new_tdx`;
- extract over the user's TDX installation;
- use an unofficial mirror as Core authority;
- use Sep-29 intraday data as completed Sep-28 data;
- relabel historical non-PIT data as PIT;
- invent first-availability timestamps;
- alter V4-04 algorithms;
- start V4-05 R2;
- start V4-06/07/08/09;
- promote any accepted head.

---

# 24. Closure

Closure report must state:

- starting HEAD;
- implementation commit;
- fresh official metadata date/time;
- each download attempt and method;
- final package SHA/bytes;
- ZIP validation;
- extraction identity;
- Sep-28 bar counts;
- overlap result;
- universe result;
- GBBQ visibility result;
- adjustment quality counts;
- sample recomputation;
- no-backdating result;
- determinism result;
- independent postcheck;
- TDX root write count;
- exact terminal status.

Stop at the candidate and wait for independent external acceptance.
