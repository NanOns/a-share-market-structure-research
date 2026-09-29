# V4-02 go-forward PIT adjustment amendment R2: candidate closure

Starting HEAD: `1524dcad312652c28b1f03b558ec8b6a7a3d0aa9`. Candidate build commit: `0f679b81133345c7778b0215e5dfdc52435af0c9`. Later-revision audit and final postcheck commit: `e666b7632f5ef1564920a501a2f566422406bfd6`. Target trade date: `2026-09-28`. Governing R2 task and R1 external audit are stored in `docs/evidence/`.

## Source and downloader

Fresh official metadata remained `HSJDAY_SOFT_TIME=2026-09-28 15:58:05`. Two Python `urllib` attempts returned HTTP 200 `text/html` bodies of 986 and 987 bytes; their bounded prefix/suffix, headers, bytes, elapsed times, and failure reasons are in `V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json`. An independent Windows `curl.exe` transfer returned an official `application/zip` package of 551,001,603 bytes. SHA256: `70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c`. ZIP structure and CRC passed. The package is frozen in project-controlled storage and committed through Git LFS. No data was written under `D:/new_tdx`.

The official package was captured on Sep-29, after its Sep-28 publication. Thus **the candidate's earliest formal system publication is after the successful capture**, as recorded in the row lineage. This candidate does not claim that the local system held raw Sep-28 bars on Sep-28 itself, nor does it claim historical bar-date AS_RECORDED adjustment.

## Package, overlap, and universe

Extraction inventory: 12,438 structurally usable `.day` files and 952,897,792 uncompressed bytes; two empty official `.day` entries were inventoried and excluded from bars. Maximum raw trade date was `20260928`, future bar count zero. The package has 9,717 Sep-28 bars across SH/SZ/BJ. The accepted required-stock Sep-24 raw overlap matched on all 5,210 accepted rows within source-normalization tolerance; no accepted-only rows or value mismatches. Package-only rows were outside that accepted stock cross-section.

The Sep-28 required-board candidate preserves all 5,222 accepted Sep-24 security identities: SH_MAIN 1,702; SZ_MAIN 1,494; CHINEXT 1,408; STAR 618. It has 5,210 actual target-date bars and 12 identities without a T0 bar. No new unresolved source key or unexplained dropped identity was found. Dated code-change identity `SZ.300114 → SZ.302132` remains mapped to its accepted security ID. BSE remains optional.

## Adjustment and quality

The frozen Sep-26 GBBQ snapshot has `system_available_at=2026-09-26T13:07:05Z`, manifest SHA256 `f8c799f999482f385a4b1d6153ae9dafe7794aff5ddabee6e718e7fd119bad32`, `gbbq` SHA256 `f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1`, and `gbbq.map` SHA256 `f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8`. Only that pre-T0 frozen event set with effective date no later than T0 drives adjustment. The versioned contract is `config/v4_02_go_forward_pit_adjustment_r2.json`; historical lookback is transformed into the **T0 current coordinate** using the accepted affine QFQ engine.

Candidate rows: 5,222. `RAW_READY=5,210`; `ADJUSTED_READY=5,195`; `ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT=15`; `ADJUSTED_UNAVAILABLE_NO_T0_RAW=12`. Unavailable securities remain in the universe and have no QFQ fallback. Real sample evidence covers cash dividend, bonus/transfer, rights issue, combined action, no-action control, no-T0-bar case, unsupported event, and the accepted code-change identity.

A later local GBBQ snapshot was copied read-only into a separate diagnostic store and compared against the frozen Sep-26 input. Comparison found 21 <=T0 additions, one <=T0 revision, one deletion, and 28 future-effective additions. **None of the <=T0 changes belonged to a price-affecting or unknown-price-impact category.** The later snapshot did not drive T0 QFQ. Its raw files, hash-bound receipt, and independent comparison are included for audit.

## Reproducibility and acceptance

Two builds from identical inputs produced the same logical digest `920118935010f2b9e5de4b76b33b7537ffdadbd3cd91ae17fae368524caaebe6` and compressed SHA256 `83d99b99603a77c24732d857fdffb44e8d20fa02e44a016c460137a5eac3eb7c`. The no-backdating negative test injected a later-only, <=T0 effective event: the frozen-source result stayed identical, whereas incorrectly consuming that event changed the factor. Independent postcheck passed package identity/ZIP, target-date bars, raw overlap samples, four-board identity, GBBQ hashes, historical QFQ sample recomputation, quality counts, determinism, no-backdating, and unchanged Accepted Heads. Focused tests: 52 passed.

Terminal status: `V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R2`. This is a **candidate for external audit**, not acceptance or Accepted Head promotion. `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`. V4-05 R2 and later stages were not started. Next stage: independent external audit of this candidate and its publication-time semantics.
