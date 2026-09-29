# V4-02 Go-Forward PIT Amendment R1 External Audit
## Raw Source Capture Blocker Review

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Audit Date:** 2026-09-29  
**Reviewed HEAD:** `1524dcad312652c28b1f03b558ec8b6a7a3d0aa9`  
**Previous Baseline:** `52ff45b138fa536e802168a11aebbba6d1cb1d9d`

---

# 0. Final Disposition

Current R1 stage result:

`V4_02_GO_FORWARD_BLOCKED_NO_COMPLETE_20260928_RAW`

External audit disposition:

`R1_BLOCK_EVIDENCE_ACCEPTED_BUT_DOWNLOAD_PIPELINE_REPAIR_REQUIRED`

The blocker is real:

- local TDX data does not contain the completed 2026-09-28 session;
- the project does not yet possess a validated project-controlled 2026-09-28 `hsjday.zip`;
- no go-forward PIT adjusted candidate can be accepted without a complete immutable raw source.

However this is **not** a user-manual-download requirement.

The repository is authorized to retrieve the public official TDX package into project-controlled storage while keeping `D:/new_tdx` read-only.

Next required work:

`TDX_OFFICIAL_RAW_CAPTURE_R2 + CONTINUE_GO_FORWARD_PIT_CANDIDATE`

---

# 1. User Environment Constraint Frozen for Next Task

Treat the following as an explicit execution constraint:

```text
local TDX usable cutoff = 2026-09-24
```

Do not expect local `D:/new_tdx` to contain 2026-09-28.

Do not stop merely because the local source is stale.

The local source remains read-only and may be used only for:

- accepted historical overlap;
- comparison;
- source diagnostics.

The missing 2026-09-28 raw source must be acquired by Codex from an approved official public source if required.

---

# 2. Changes Reviewed

Commits after the prior V4-05 blocker seal:

```text
7042c6385daded8a9f4bee0360a72e8d73304270
[V4-02] Record go-forward PIT raw source blocker

d77ec3977b8d82342e85b3cbb99d4bed30fc5d1d
[V4-02] Seal go-forward PIT source blocker postcheck

1524dcad312652c28b1f03b558ec8b6a7a3d0aa9
[V4-02] Normalize sealed source evidence hashes
```

No accepted head was modified.

No go-forward PIT candidate was falsely promoted.

---

# 3. Official Publication Evidence

The captured official TDX page contains the official package link:

`https://data.tdx.com.cn/vipdoc/hsjday.zip`

The captured official update metadata states:

```text
HSJDAY_SOFT_SIZE = 525.47MB
HSJDAY_SOFT_TIME = 2026-09-28 15:58:05
```

Therefore the official publication layer showed a completed Sep-28 full daily package.

This rules out:

```text
NO_OFFICIAL_20260928_PUBLICATION
```

as the blocker.

The blocker is instead:

```text
OFFICIAL_PACKAGE_CAPTURE_FAILED
```

---

# 4. Local TDX Probe

R1 inspected the user's TDX root read-only.

It found no Sep-28 terminal records in SH/SZ.

This is consistent with the frozen execution constraint that the local data is only current through Sep-24.

The probe correctly did not modify:

`D:/new_tdx`

`tdx_root_write_count = 0`

**PASS**

---

# 5. Official Download Attempt

Recorded attempt:

```text
python scripts/capture_tdx_official_daily_package.py
  --target-date 2026-09-28
```

Result:

```text
BLOCKED_TDX_SOURCE_CAPTURE
reason = TDX_ZIP_INVALID
```

No invalid archive was promoted.

No false source snapshot was created.

**Correct fail-closed behavior**

---

# 6. Downloader Audit Finding D01
## Failure is not diagnostically sufficient

`TDX_ZIP_INVALID` is thrown only after the stream has already been downloaded and `zipfile.ZipFile()` rejects the body.

But the failure receipt does not preserve enough bounded evidence to tell whether the response was:

- an HTML error page;
- CDN/WAF response;
- proxy page;
- partial binary body;
- corrupted ZIP;
- unexpected content encoding;
- another server-side payload.

Missing failure evidence includes:

```text
final_url
HTTP status
Content-Type
Content-Length
ETag
Last-Modified
Content-Disposition
actual byte_count
first bounded response bytes / magic
last bounded bytes / EOCD diagnostic
download method
attempt number
elapsed time
```

Because the invalid body is deleted immediately, the root cause cannot be independently diagnosed.

**Finding: REPAIR REQUIRED**

---

# 7. Downloader Audit Finding D02
## Single transfer path is too brittle for a 525MB official package

The official package is approximately 525MB.

The current implementation effectively relies on one Python `urllib` transfer path.

There is no stage-level policy for:

- retry with backoff;
- reconnect after transient failure;
- browser-like `Referer`;
- alternate official transfer client;
- resumable transfer;
- independent ZIP validation after an alternate download;
- comparing SHA of repeated successful captures.

One failed Python transfer must not by itself become:

`NO_COMPLETE_RAW_SOURCE`

when the official page itself advertises the package.

**Finding: REPAIR REQUIRED**

---

# 8. Downloader Audit Finding D03
## The official source URL is correct

The page-discovered URL is the expected TDX full daily package URL.

The failure is not evidence that the URL should be replaced with a third-party mirror.

Next task must remain restricted to official TDX domains.

Allowed origin:

```text
www.tdx.com.cn
data.tdx.com.cn
```

Third-party mirrors are not required and must not become the authoritative Core source.

---

# 9. Downloader Audit Finding D04
## Package layout validation should be robust to official ZIP path encoding

The existing validator normalizes backslashes, which is useful.

The next revision should validate `.day` entries by semantic path components and not rely unnecessarily on one ZIP writer's exact separator/root layout.

Accept only safe official layouts that resolve to:

```text
sh/.../*.day
sz/.../*.day
bj/.../*.day
```

or an allowed single top-level wrapper followed by the same market hierarchy.

Path traversal/symlink/duplicate protections remain mandatory.

This is not proven to be the current `BadZipFile` cause, but should be closed while the downloader is repaired.

---

# 10. R1 Source Gate

`V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_R1.json`

truthfully records:

```text
valid_project_controlled_20260928_package_count = 0
status = V4_02_GO_FORWARD_BLOCKED_NO_COMPLETE_20260928_RAW
```

The downstream gates were correctly not run.

**PASS for blocker evidence only**

---

# 11. Independent Postcheck

The independent postcheck confirms:

- capture receipt hash;
- official update-info hash;
- no validated Sep-28 project archive;
- no local Sep-28 SH/SZ final bars;
- Sep-26 GBBQ identity;
- historical AS_RECORDED remains blocked;
- accepted heads unchanged.

Status:

`PASS_FOR_BLOCK_EVIDENCE_ONLY`

**Accepted**

---

# 12. What Must Not Happen Next

Do not require the user to manually download the Sep-28 package.

Do not write the ZIP into or extract it over:

`D:/new_tdx`

Do not relax source authority to an arbitrary mirror.

Do not use 2026-09-29 intraday data as a completed daily substitute.

Do not label a later package as a Sep-28 PIT snapshot if the official metadata has already rolled forward and the Sep-28 archive bytes were never successfully frozen.

Do not run adjustment/profile replay until a valid raw source is frozen.

---

# 13. Required Next Direction

The next task must:

1. repair the official package downloader;
2. acquire the complete official package automatically;
3. store it under project-controlled immutable snapshot storage;
4. independently validate ZIP structure and SHA;
5. prove target-date content;
6. run accepted-history overlap checks;
7. extend the target-date universe/identity candidate;
8. continue the previously blocked go-forward PIT adjustment candidate;
9. stop at candidate for external audit.

If the official package has rolled beyond Sep-28 before a valid Sep-28 archive is frozen, issue a precise rollover blocker and freeze evidence for the next provable forward date instead of fabricating Sep-28 provenance.

---

# 14. Final Status

```text
R1_BLOCK_EVIDENCE = ACCEPTED

LOCAL_TDX_20260928 = NOT_AVAILABLE_EXPECTED

OFFICIAL_20260928_PUBLICATION = OBSERVED

OFFICIAL_ARCHIVE_CAPTURE = FAILED_TDX_ZIP_INVALID

GO_FORWARD_PIT_ADJUSTMENT = NOT_ACCEPTED

NEXT =
TDX_OFFICIAL_RAW_CAPTURE_R2
+
GO_FORWARD_PIT_CANDIDATE_CONTINUATION
```
