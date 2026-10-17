---
stage_id: V4_R21_NONOWNER_FILE_READ_MECHANISM_AUDIT_20261017_R1
baseline_inventory_head: 81f7398d52a786a0c0d4570a988f6aeeabf9b3f5
current_code_head_at_analysis: c473a653172caa5389c2a85f134ce59ded2ee1a8
scope: 38 external market-data reads and 28 other business-file reads
method: targeted callsite and caller-path mechanism review using accepted R20 inventories; no full R19/R20 rescan
conclusion: MECHANISM_REVIEW_COMPLETE_MIGRATION_AND_RUNTIME_ACCEPTANCE_OPEN
formal_p1_remaining: 266
live_pg_readback: NOT_RUN_NO_CONFIGURED_V4_NATIVE_PG_DSN
production_or_head_change: NONE
---

# V4 R21 non-Owner file-read mechanism audit R1

Date: 2026-10-17 (Asia/Shanghai). This review is limited to the 38 `EXTERNAL_BUSINESS_DATA_FILE_READ_REQUIRES_DB` rows and the 28 `BUSINESS_FILE_READ_REQUIRES_DB` rows in the accepted R20 business inventory. It reuses that inventory and its R20 full-reference evidence; it does not repeat the full R19/R20 static audit. The source baseline is `81f7398d52a786a0c0d4570a988f6aeeabf9b3f5`; R21 changes were inspected at `c473a653172caa5389c2a85f134ce59ded2ee1a`.

## Executive result

- The 38 market-data rows span 11 files. They describe a mix of network response/package ingress, local TDX package reads, snapshot and manifest verification, membership-history parsing, fallback reads, and parent/current archive comparison. These are not 38 independent datasets and not all are downstream consumer reads. Their correct target is a contracted ingress boundary followed by PG persistence and PG-only downstream consumption.
- All 38 market-data rows remain `OPEN` in the R21 matrix. Twenty-two rows have exact reference-inventory IDs; 16 have no exact path+line edge and need source-edge reconciliation. The 38 inventory rows contain only 36 distinct BCA IDs: both ZIP-delta modules count parent and current archive opens on the same source line under one duplicated ID. The matrix row count is preserved, but evidence closure must add API/path-argument identity so the two reads cannot be conflated. The TDX root and downloader-receipt changes reduce path ambiguity but do not implement data ingestion or remove the underlying market-data P1 findings.
- The 28 other business-file rows span 21 files. Eighteen read mutable Head/index state (accepted stage, data, operational, producer-candidate identity); ten read contract, seal, gate, or historical stage-receipt files. All 28 map to exact reference IDs. Current R21 matrix status is 26 `OPEN`, one code-level PG-only identity-reader migration pending inventory reconciliation, and one retained source-ingress/head read. Thus these classes have distinct migration treatment; a filename under `reports/` is not automatically an invariant contract.
- No row is removed from the formal P1 count by this review. The formal count remains 266 pending inventory reconciliation. Static callsite inspection does not establish invocation frequency or current production reachability; no live PG readback or runtime trace was performed.

## Mechanism analysis: 38 external market-data reads

### Flow and trust boundary

The mechanisms form a producer-side chain: fetch or select an external/local source; verify URL/root, package bytes, archive members, receipt and snapshot identity; parse or compare target-session data; then pass a source binding into a producer. Files are useful at the ingress edge for bounded acquisition, hashing, and parser input. The durable accepted fact and every later business consumer must be addressed by a PG authority/Owner identity. The source-root constraint remains: TDX source roots are read-only, and all generated outputs must be elsewhere and atomically written.

| Mechanism family | Rows / files | What the code reads and why | PG-only migration boundary and open evidence |
|---|---:|---|---|
| Official daily package | 8 / `tdx_official_daily_source.py` | Bounded official-site requests and update metadata; streamed package bytes; ZIP structure; downloaded/previous package, receipt, rejection marker and prior receipt. These reads support source discovery, integrity checks, date selection and idempotent reuse. | Keep only the approved bounded request and one-time raw-byte ingress at the adapter. Bind source URL/issuer, request/response timestamps, target session, original SHA-256, byte count, archive/member manifest, parser/version and receipt into a versioned source contract. Persist normalized unadjusted bars and source attestations to a PG Owner; serve downstream reads from PG. Prove no silent older-package substitution and fail closed on malformed, stale or mismatched receipts. |
| Latest-package adapter | 6 / `tdx_latest_daily_source_v2.py` | Validates package endpoint behavior, consumes the downloader’s exact pointer/receipt, reads cached/extracted output and the package ZIP, then extracts target-session bars. | The R21 change removes implicit TDX-root fallback and switches to the exact receipt returned by the bounded downloader. That is an ingress safety fix only. Still open: explicit dataset capability gate, issuer allowlist, request timestamp/session semantics, size/redirect limits, original archive/member digests, parser contract, and PG write/readback evidence. A cache is not accepted business authority. |
| Local daily fallback | 4 / `tdx_local_daily_fallback_v1.py` | Reads the selected original archive and bytes, then a temporary package and receipt to recover daily rows. This is an alternate acquisition route, not merely a filesystem cache hit. | Model fallback as a separately gated source in the versioned source contract. Preserve which source actually supplied the rows, why fallback activated, timestamp and raw digest. Never merge silently or let fallback rewrite the local snapshot identity. Temporary files remain disposable G-drive data; final accepted facts must be in PG. |
| Local snapshot build/verify | 4 / `tdx_local_snapshot.py` | Opens and hashes TDX source files, reads prior snapshot metadata and a manifest, then verifies a snapshot ID against captured bytes. | Treat source-root traversal as a read-only ingest operation. Preserve relative source path, immutable source root identity, file SHA-256/size, capture timestamp and snapshot contract. Store the accepted snapshot manifest/row facts in PG; keep only transient build files outside the source root. Reconcile symlink/reparse protections, manifest freshness and exact source membership with the PG contract. |
| TDX archive integrity and deltas | 8 / `tdx_snapshot.py`, `tdx_snapshot_delta.py`, `tdx_snapshot_delta_v2.py` | Hashes ZIP files, verifies archive entries, opens members, and compares parent/current packages to calculate untyped or typed deltas. The typed variant also uses identity bindings and target dates. | Parent and current packages need separately bound source IDs, dates, hashes, namespace and parser/identity version in PG. Delta facts must be reproducible from the two accepted source identities and stored as versioned derived facts; no filesystem path or mutable “latest” pointer can be the authority. Preserve deletions, renames, duplicate members and identity-map changes. |
| Membership retro parser | 5 / `tdx_member_retro_r43.py` | Reads a frozen copy and source code/member files, reparses for verification, captures normalized membership rows and checks date/identity validity. | Keep the original membership file as read-only source evidence. Ingest dated membership rows with effective-date/as-of semantics, source SHA, identity mapping version and parser version. Retro corrections must be a new immutable revision with explicit effective date; do not overwrite prior membership history or infer PIT from current constituent data. |
| Producer wrapper/bootstrap and evidence receipt | 3 / `capture_dm01_a01_r3_tdx_package.py`, `producer_bootstrap_v1.py`, `r43_operational_sources.py` | The wrapper opens the archive; bootstrap reads an artifact path from a binding and also opens the current operational Head; the operational-source adapter reads a fixed evidence receipt under `docs/evidence`. These are orchestration and source-binding reads, not three separate market APIs. | Resolve the receipt/Head/artifact chain to one accepted source contract and pass typed source IDs to producers. The evidence-receipt path needs an explicit classification: immutable source receipt versus historical process evidence. No consumer should reopen the package by path after PG ingestion. Do not treat archive receipt success as PG ingestion or source acceptance. |

### Cross-cutting market-data risks

1. **Ingress and consumer reads are mixed in one P1 class.** The code needs a narrow filesystem/network ingress exception with explicit capability gates; downstream market-data consumers should have no TDX path fallback. Each of the 38 rows must be tagged `INGRESS`, `VALIDATION`, or `CONSUMER` with a verified caller chain before closure.
2. **“Latest” is a request-time selector, not a stable identity.** Persist request time, source-reported update time, exchange session, acquisition sequence and the exact digest. A cache or downloader pointer cannot stand in for immutable source identity.
3. **Original and derived identity must remain separate.** Preserve original archive hash and TDX relative file/member hashes. Store parser output and delta as derived PG facts with `derived_from` source identities. Do not alter snapshot IDs when relocating reads to PG.
4. **Fallback is an authority choice.** It needs an explicit per-dataset enablement and audit record. On missing, stale or conflicting evidence, close the affected capability and report `DEGRADED_PASS`/`BLOCKED` according to the source contract.
5. **No external adjustment service or future information.** Any source contract must explicitly prohibit external adjustment data, future rows, automated trading and probabilistic claims; retain raw/unadjusted basis and exchange-date semantics.

## Mechanism analysis: 28 other business-file reads

### Mutable accepted identity and producer state: 18 callsites

These reads select the currently accepted stage/data/operational head, a producer candidate index, a calendar binding, or current source cut-off. They control which data and contracts a producer or page may see. They are mutable business authority even where the file only contains pointers and digests. The PG replacement is a read-only transaction against the appropriate existing typed Head/Owner relation, keyed by contract/version, namespace and accepted identity; it must return the exact source bindings and publication/session metadata. Do not replace one JSON pointer with a generic “current” database lookup that loses historical version or T0.

- `V4_STAGE_ACCEPTED_HEAD` and `V4_05_ACCEPTED_HEAD`: stage promotion and accepted predecessor selection in replay, stock prewatch, V4.13 package/descendant dispatch, and current-stage authority.
- `V4_DATA_ACCEPTED_HEAD`: current calendar/identity selection for incremental builders, historical stage state, market sessions, membership search-identity preparation, and the current product identity reader. The BFF identity read path was changed to a typed PG reader in the R21 batch; formal reconciliation remains open.
- `V4_OPERATIONAL_RESEARCH_HEAD`: accepted trade-date cutoff and current operational authority in producer bootstrap, daily executor and daily server. Replace both server path reads and producer guards with one transactionally consistent PG head read.
- `producer_candidate_index_v2.json`: selects dated, non-production candidate sidecars consumed by `prepare_research`; migrate it to a PG candidate/session registry keyed by candidate ID, date and source-owner digest.
- `start_product_attested_r4.py`: reads hashes of operational and data Heads to protect against unexpected mutation while startup/attestation runs. Replace the file-hash guard with a PG identity snapshot (and compare the same immutable authority tuple before/after the protected step); do not remove the guard.

### Contract, seal, gate and historical receipt: 10 callsites

These reads select implementation contracts, sealed producer sets, local gate outcomes, or an accepted historical dataset. They cannot be exempted merely because their paths are under `reports/`. For each artifact, establish whether it is (a) immutable, source-controlled invariant configuration with a contract ID/version/digest and no run-specific business state, or (b) mutable acceptance/publication state that must be stored in PG. The latter includes gate result, accepted publication, selected dataset and lineage. Keep a versioned invariant artifact on file only when the repository policy explicitly classifies it as such and the loader validates its exact identity.

- V4.09 freeze and repair freeze (`stock_prewatch.py`): two artifacts gate package validation; the separate accepted stage/head selects authority. Migrate run-specific acceptance state; classify the frozen rule contract separately.
- V4.10 freeze (`research_state.py`): fixed contract selection for research package construction; bind contract version/digest and ensure no mutable publication state is embedded.
- V4.11 R3/R4 sealed producer sets (`target_fact_producers_r3.py`, `target_fact_producers_r4.py`): select which producer is allowed for a publication date. This is authority/allowlist state; prove it is immutable contract policy or represent it as a versioned PG producer registry.
- P12/P13 stage gate and dataset manifest (`history_170_v3_3.py`): the gate receipt selects a dataset path, then the manifest output digest is checked. This is historical business dataset authority and should resolve to an accepted PG publication/manifest with immutable source digest, not a mutable directory path.
- V4.12 local gate (`v4_12_breakout_snapshot.py`, `v4_12_frozen_snapshot_v2.py`): two consumer paths independently read the same gate. Consolidate to one shared typed contract/gate reader; distinguish static contract digest from mutable pass/fail evidence.
- V4.13 amendment (`v4_13_io.py`): loads amendment contract family; classify the amendment as an immutable versioned invariant or store active selection in PG.

### Closure gates

The 28 callsites all have an exact R20 reference ID edge, but that proves a crosswalk only, not runtime reachability, use, or a safe replacement. The R21 matrix records 26 still open, one PG-only code migration pending business-inventory reconciliation, and one retained membership-source preparation read. The latter reads the current data Head while preparing a new search-identity reference; it belongs at a controlled source-ingress/publisher boundary, not a live page consumer. Its exact input still needs a declared T0/source identity and PG ingestion acceptance path.

For every row before closing P1: record caller chain and reachability; specify Owner or invariant contract ID/version; define relation/schema/database identity; preserve T0, publication/revision, source digest and namespace; prove completeness/denominator and field parity; test missing/stale/conflict as fail-closed; and reconcile the business inventory against source hashes. A code-only migration is not live PG readback or production acceptance.

## Callsite-level evidence appendix

The following tables transcribe the accepted R20 read rows and join each by normalized path plus baseline line to the R21 matrix. The local row number distinguishes multiple read expressions recorded on one source line; in the two ZIP-delta cases the source inventory BCA ID is duplicated across parent/current archive opens. `UNMAPPED` means no exact reference edge was found. `OPEN` is the current matrix status; it does not mean the code is proven active at runtime.

### 38 external market-data reads

| Row | Callsite ID | Baseline location / function | Read mechanism and path expression | Reference IDs | R21 code status |
|---:|---|---|---|---|---|
| MKT-01 | `V4-BCA-R2-78d61b55d2259e7f1c21` | `scripts/capture_dm01_a01_r3_tdx_package.py:48`<br>`main` | `archive.read_text`<br>`archive` | UNMAPPED | `OPEN` |
| MKT-02 | `V4-BCA-R2-a6da78337e0871cef36b` | `src/workbench_analysis/producer_bootstrap_v1.py:22`<br>`capture_daily_sources` | `read_bytes`<br>`Path(artifact['tdx']['path'])` | V4-NCFR-0160165, V4-NCFR-0160176 | `OPEN` |
| MKT-03 | `V4-BCA-R2-3a56abc56d7cc5fc0f0f` | `src/workbench_analysis/r43_operational_sources.py:36`<br>`run_sources` | `read_bytes`<br>`root/'docs/evidence/r4_2_1_20261009/TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json'` | V4-NCFR-0160213, V4-NCFR-0160215 | `OPEN` |
| MKT-04 | `V4-BCA-R2-0d228b8f6c31ed9b1f76` | `src/workbench_analysis/tdx_latest_daily_source_v2.py:16`<br>`_package_validator` | `open`<br>`urllib.request.build_opener(old._AllowlistedRedirect())` | V4-NCFR-0160282 | `OPEN` |
| MKT-05 | `V4-BCA-R2-30490ac5aecfd423e85b` | `src/workbench_analysis/tdx_latest_daily_source_v2.py:57`<br>`capture_latest_tdx_package` | `pointer.read_bytes`<br>`pointer` | V4-NCFR-0160283 | `OPEN` |
| MKT-06 | `V4-BCA-R2-1432146ab8da14bec80d` | `src/workbench_analysis/tdx_latest_daily_source_v2.py:90`<br>`extract_target_session_bars` | `cache.read_bytes`<br>`cache` | V4-NCFR-0160284 | `OPEN` |
| MKT-07 | `V4-BCA-R2-c862a3540096d320fcb9` | `src/workbench_analysis/tdx_latest_daily_source_v2.py:92`<br>`extract_target_session_bars` | `artifact.read_bytes`<br>`artifact` | V4-NCFR-0160286 | `OPEN` |
| MKT-08 | `V4-BCA-R2-94dfbfdfad7f9e2ff006` | `src/workbench_analysis/tdx_latest_daily_source_v2.py:97`<br>`extract_target_session_bars` | `zipfile.ZipFile`<br>`package` | V4-NCFR-0160285 | `OPEN` |
| MKT-09 | `V4-BCA-R2-f085f3b0ceb25cf91b65` | `src/workbench_analysis/tdx_latest_daily_source_v2.py:144`<br>`extract_target_session_bars` | `output.read_bytes`<br>`output` | UNMAPPED | `OPEN` |
| MKT-10 | `V4-BCA-R2-d85b9178c81b9f1f62fe` | `src/workbench_analysis/tdx_local_daily_fallback_v1.py:25`<br>`fallback` | `zipfile.ZipFile`<br>`original` | V4-NCFR-0160287 | `OPEN` |
| MKT-11 | `V4-BCA-R2-b27ea1de27ada027ba55` | `src/workbench_analysis/tdx_local_daily_fallback_v1.py:32`<br>`fallback` | `path.read_bytes`<br>`path` | UNMAPPED | `OPEN` |
| MKT-12 | `V4-BCA-R2-99269cbe5cf6215f9d67` | `src/workbench_analysis/tdx_local_daily_fallback_v1.py:69`<br>`fallback` | `zipfile.ZipFile`<br>`temp` | V4-NCFR-0160289 | `OPEN` |
| MKT-13 | `V4-BCA-R2-f6c8d8313ae78fe2a109` | `src/workbench_analysis/tdx_local_daily_fallback_v1.py:82`<br>`fallback` | `receipt_path.read_bytes`<br>`receipt_path` | V4-NCFR-0160288 | `OPEN` |
| MKT-14 | `V4-BCA-R2-cb4d2d0cf9588ab70596` | `src/workbench_analysis/tdx_local_snapshot.py:21`<br>`_sha256` | `path.open`<br>`path` | UNMAPPED | `OPEN` |
| MKT-15 | `V4-BCA-R2-ff23e65e50af198a10d6` | `src/workbench_analysis/tdx_local_snapshot.py:87`<br>`build_local_snapshot` | `source_file.open`<br>`source_file` | UNMAPPED | `OPEN` |
| MKT-16 | `V4-BCA-R2-721363b0d7e464ce0780` | `src/workbench_analysis/tdx_local_snapshot.py:130`<br>`build_local_snapshot` | `prior_path.read_text`<br>`prior_path` | V4-NCFR-0160292 | `OPEN` |
| MKT-17 | `V4-BCA-R2-9886459358289c371470` | `src/workbench_analysis/tdx_local_snapshot.py:152`<br>`verify_local_snapshot` | `manifest_path.read_text`<br>`manifest_path` | V4-NCFR-0160291 | `OPEN` |
| MKT-18 | `V4-BCA-R2-14162403b4df951c16e0` | `src/workbench_analysis/tdx_member_retro_r43.py:57`<br>`parse_frozen_rows` | `copy.read_bytes`<br>`copy` | UNMAPPED | `OPEN` |
| MKT-19 | `V4-BCA-R2-0f607d99a7bab71ac386` | `src/workbench_analysis/tdx_member_retro_r43.py:115`<br>`reparse_verification` | `code.read_bytes`<br>`code` | UNMAPPED | `OPEN` |
| MKT-20 | `V4-BCA-R2-a8cb3289dd02647d0a7a` | `src/workbench_analysis/tdx_member_retro_r43.py:117`<br>`reparse_verification` | `code.read_bytes`<br>`code` | UNMAPPED | `OPEN` |
| MKT-21 | `V4-BCA-R2-a329718a6cfd459f6aaf` | `src/workbench_analysis/tdx_member_retro_r43.py:139`<br>`capture` | `source.read_bytes`<br>`source` | UNMAPPED | `OPEN` |
| MKT-22 | `V4-BCA-R2-04f2f057eb1865452039` | `src/workbench_analysis/tdx_member_retro_r43.py:170`<br>`capture` | `p.read_bytes`<br>`p` | UNMAPPED | `OPEN` |
| MKT-23 | `V4-BCA-R2-20ecaf065eae11c8b715` | `src/workbench_analysis/tdx_official_daily_source.py:65`<br>`_request` | `opener.open`<br>`opener` | UNMAPPED | `OPEN` |
| MKT-24 | `V4-BCA-R2-bec2c850723a53aedcae` | `src/workbench_analysis/tdx_official_daily_source.py:151`<br>`sha256_file` | `path.open`<br>`path` | UNMAPPED | `OPEN` |
| MKT-25 | `V4-BCA-R2-ad3b4050f4b799bb2a58` | `src/workbench_analysis/tdx_official_daily_source.py:174`<br>`_zip_validate` | `zipfile.ZipFile`<br>`path` | V4-NCFR-0160295 | `OPEN` |
| MKT-26 | `V4-BCA-R2-1f43c11985168a9f42f8` | `src/workbench_analysis/tdx_official_daily_source.py:269`<br>`verified` | `pointer.read_bytes`<br>`pointer` | V4-NCFR-0160296 | `OPEN` |
| MKT-27 | `V4-BCA-R2-27beab2ff6c744fc1f15` | `src/workbench_analysis/tdx_official_daily_source.py:274`<br>`verified` | `receipt_path.read_bytes`<br>`receipt_path` | V4-NCFR-0160294 | `OPEN` |
| MKT-28 | `V4-BCA-R2-f529aa4868e4eb6885e1` | `src/workbench_analysis/tdx_official_daily_source.py:395`<br>`capture_tdx_official_daily_package` | `rejected.read_bytes`<br>`rejected` | UNMAPPED | `OPEN` |
| MKT-29 | `V4-BCA-R2-647e0bc90a5a84ef8840` | `src/workbench_analysis/tdx_official_daily_source.py:430`<br>`capture_tdx_official_daily_package` | `source.read_bytes`<br>`source` | UNMAPPED | `OPEN` |
| MKT-30 | `V4-BCA-R2-4e47dfd44b8d4d0dac5c` | `src/workbench_analysis/tdx_official_daily_source.py:437`<br>`capture_tdx_official_daily_package` | `prior_receipt.read_text`<br>`prior_receipt` | V4-NCFR-0160298 | `OPEN` |
| MKT-31 | `V4-BCA-R2-fef425b5b05ae269e51b` | `src/workbench_analysis/tdx_snapshot.py:16`<br>`sha256_file` | `path.open`<br>`path` | UNMAPPED | `OPEN` |
| MKT-32 | `V4-BCA-R2-fdfa20ff47bf7f0414b0` | `src/workbench_analysis/tdx_snapshot.py:57`<br>`verify_zip_snapshot` | `zipfile.ZipFile`<br>`archive_path` | V4-NCFR-0160300 | `OPEN` |
| MKT-33 | `V4-BCA-R2-6b1159b92eade8307b9c` | `src/workbench_analysis/tdx_snapshot.py:94`<br>`verify_zip_snapshot` | `archive.open`<br>`archive` | UNMAPPED | `OPEN` |
| MKT-34 | `V4-BCA-R2-599f105a1ba3ebedc3f0` | `src/workbench_analysis/tdx_snapshot_delta.py:96`<br>`build_tdx_package_delta` | `zipfile.ZipFile`<br>`parent_zip` | V4-NCFR-0160301, V4-NCFR-0160302 | `OPEN` |
| MKT-35 | `V4-BCA-R2-599f105a1ba3ebedc3f0` | `src/workbench_analysis/tdx_snapshot_delta.py:96`<br>`build_tdx_package_delta` | `zipfile.ZipFile`<br>`current_zip` | V4-NCFR-0160301, V4-NCFR-0160302 | `OPEN` |
| MKT-36 | `V4-BCA-R2-9104fc37a24acef63198` | `src/workbench_analysis/tdx_snapshot_delta_v2.py:26`<br>`file_sha` | `open`<br>`Path(path)` | V4-NCFR-0160303 | `OPEN` |
| MKT-37 | `V4-BCA-R2-bd02fac29a4934e29be7` | `src/workbench_analysis/tdx_snapshot_delta_v2.py:85`<br>`build_typed_delta` | `zipfile.ZipFile`<br>`parent_zip` | V4-NCFR-0160304, V4-NCFR-0160305 | `OPEN` |
| MKT-38 | `V4-BCA-R2-bd02fac29a4934e29be7` | `src/workbench_analysis/tdx_snapshot_delta_v2.py:85`<br>`build_typed_delta` | `zipfile.ZipFile`<br>`current_zip` | V4-NCFR-0160304, V4-NCFR-0160305 | `OPEN` |

### 28 other business-file reads

| Row | Callsite ID | Baseline location / function | Read mechanism and path expression | Reference IDs | R21 code status |
|---:|---|---|---|---|---|
| OTH-01 | `V4-BCA-R2-5e40998af6195505feae` | `scripts/start_product_attested_r4.py:41`<br>`owned_main` | `read_bytes`<br>`ROOT/'data/v4'/name` | V4-NCFR-0156962 | `OPEN` |
| OTH-02 | `V4-BCA-R2-97c1bd0ed538b4e13a26` | `src/v4/replay_inputs.py:35`<br>`resolve` | `read_text`<br>`root / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"` | V4-NCFR-0159693, V4-NCFR-0159697 | `OPEN` |
| OTH-03 | `V4-BCA-R2-1f75e66631a4f75b9b4d` | `src/v4/research_state.py:17`<br>`load_package` | `read_text`<br>`ROOT/'reports/v4_10/V4_10_R1_2_CONTRACT_FREEZE.json'` | V4-NCFR-0159700, V4-NCFR-0159701 | `OPEN` |
| OTH-04 | `V4-BCA-R2-6d4ef91c0b4d003f6592` | `src/v4/stock_prewatch.py:45`<br>`_validate_repair_freeze` | `read_text`<br>`root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'` | V4-NCFR-0159720, V4-NCFR-0159730 | `OPEN` |
| OTH-05 | `V4-BCA-R2-d5e5df9904f34026c94a` | `src/v4/stock_prewatch.py:67`<br>`load_package` | `read_text`<br>`root/'reports/v4_09/V4_09_CONTRACT_FREEZE.json'` | V4-NCFR-0159723, V4-NCFR-0159731 | `OPEN` |
| OTH-06 | `V4-BCA-R2-564cec95e2fd86a126c6` | `src/v4/stock_prewatch.py:75`<br>`load_package` | `read_text`<br>`root/'reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json'` | V4-NCFR-0159724, V4-NCFR-0159733 | `OPEN` |
| OTH-07 | `V4-BCA-R2-e2d48f0a5cf852d911bd` | `src/v4/stock_prewatch.py:250`<br>`load_accepted` | `read_text`<br>`root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'` | V4-NCFR-0159725, V4-NCFR-0159734 | `OPEN` |
| OTH-08 | `V4-BCA-R2-f78e45c874a47e4393b1` | `src/v4/stock_prewatch.py:272`<br>`load_accepted` | `read_text`<br>`root/'data/v4/V4_05_ACCEPTED_HEAD.json'` | V4-NCFR-0159729, V4-NCFR-0159736 | `OPEN` |
| OTH-09 | `V4-BCA-R2-30b53176558c40e5aba6` | `src/v4/target_fact_producers_r3.py:87`<br>`validate` | `read_bytes`<br>`Path(root)/'reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json'` | V4-NCFR-0159740, V4-NCFR-0159741 | `OPEN` |
| OTH-10 | `V4-BCA-R2-c8864d2dc9053ea330ea` | `src/v4/target_fact_producers_r4.py:87`<br>`validate` | `read_bytes`<br>`Path(root)/'reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json'` | V4-NCFR-0159744, V4-NCFR-0159745 | `OPEN` |
| OTH-11 | `V4-BCA-R2-636d6fc678f581bc984c` | `src/workbench_analysis/dm01_incremental_component_builders.py:135`<br>`_context` | `read_text`<br>`ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json'` | V4-NCFR-0159841, V4-NCFR-0159842 | `OPEN` |
| OTH-12 | `V4-BCA-R2-c53955269a0f76785382` | `src/workbench_analysis/historical_stage_governance_r17.py:62`<br>`current_state` | `read_bytes`<br>`root/'data/v4/V4_DATA_ACCEPTED_HEAD.json'` | V4-NCFR-0159964, V4-NCFR-0159965, V4-NCFR-0159968, V4-NCFR-0159969 | `OPEN` |
| OTH-13 | `V4-BCA-R2-3a03bb9b0ef3ec4fa6a3` | `src/workbench_analysis/history_170_v3_3.py:13`<br>`resolve_dataset` | `read_text`<br>`root/"reports/p12_13/p12_13_170_stage_gate.json"` | V4-NCFR-0159972, V4-NCFR-0159973, V4-NCFR-0159975, V4-NCFR-0159976 | `OPEN` |
| OTH-14 | `V4-BCA-R2-66c06ef7f4ecead04533` | `src/workbench_analysis/market_source_acquisition.py:46`<br>`official_sessions` | `read_bytes`<br>`root / 'data/v4/V4_DATA_ACCEPTED_HEAD.json'` | V4-NCFR-0159982, V4-NCFR-0159985 | `OPEN` |
| OTH-15 | `V4-BCA-R2-928e5423aa7c5ec455a8` | `src/workbench_analysis/operational_daily_executor_v1.py:111`<br>`execute_sources` | `read_bytes`<br>`root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'` | V4-NCFR-0160026, V4-NCFR-0160033 | `OPEN` |
| OTH-16 | `V4-BCA-R2-251b6859286f1bec50bc` | `src/workbench_analysis/operational_daily_executor_v1.py:275`<br>`derive_ready_sources` | `read_bytes`<br>`root/'data/v4/producer_candidate_index_v2.json'` | V4-NCFR-0160030, V4-NCFR-0160036 | `OPEN` |
| OTH-17 | `V4-BCA-R2-ea189124978ab5ceb6e3` | `src/workbench_analysis/producer_bootstrap_v1.py:14`<br>`capture_daily_sources` | `read_bytes`<br>`root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'` | V4-NCFR-0160161, V4-NCFR-0160172 | `OPEN` |
| OTH-18 | `V4-BCA-R2-0a924f66fca35bcbdca9` | `src/workbench_analysis/v4_12_breakout_snapshot.py:11`<br>`load_contract` | `read_bytes`<br>`c.root/'reports/v4_12_runtime_r12/R12A_CONTRACT_LOCAL_GATE.json'` | V4-NCFR-0160319, V4-NCFR-0160320 | `OPEN` |
| OTH-19 | `V4-BCA-R2-bda5b564513151663d58` | `src/workbench_analysis/v4_12_frozen_snapshot_v2.py:10`<br>`load_contract` | `read_bytes`<br>`c.root/'reports/v4_12_runtime_r12/R12A_CONTRACT_LOCAL_GATE.json'` | V4-NCFR-0160325, V4-NCFR-0160326 | `OPEN` |
| OTH-20 | `V4-BCA-R2-2cb639250c827120ff1f` | `src/workbench_analysis/v4_13_accepted_contract_package.py:14`<br>`__init__` | `read_bytes`<br>`self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'` | V4-NCFR-0160333, V4-NCFR-0160342 | `OPEN` |
| OTH-21 | `V4-BCA-R2-7ab6593aec1a41af62f8` | `src/workbench_analysis/v4_13_accepted_contract_package.py:90`<br>`current_contracts` | `read_bytes`<br>`Path(root)/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'` | V4-NCFR-0160332, V4-NCFR-0160341 | `OPEN` |
| OTH-22 | `V4-BCA-R2-90bf20dac784077471d8` | `src/workbench_analysis/v4_13_descendant_contracts.py:21`<br>`__init__` | `read_bytes`<br>`self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'` | V4-NCFR-0160349, V4-NCFR-0160352 | `OPEN` |
| OTH-23 | `V4-BCA-R2-dfd57a91c2a1c4ba506f` | `src/workbench_analysis/v4_13_io.py:70`<br>`__init__` | `read_bytes`<br>`self.root/'reports/v4_13_r1_1/V4_13_CONTRACT_AMENDMENT_R1_1.json'` | V4-NCFR-0160365, V4-NCFR-0160370 | `OPEN` |
| OTH-24 | `V4-BCA-R2-5449a5ab84444f669574` | `src/workbench_analysis/v4_current_stage_authority.py:13`<br>`__init__` | `read_bytes`<br>`self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'` | V4-NCFR-0160437, V4-NCFR-0160449 | `OPEN` |
| OTH-25 | `V4-BCA-R2-cebee7277badb03eb82f` | `src/workbench_db/v4_membership_reference_pg_v1.py:107`<br>`prepare_search_identity` | `read_bytes`<br>`root/'data/v4/V4_DATA_ACCEPTED_HEAD.json'` | V4-NCFR-0160542, V4-NCFR-0160559 | `ACTIVE_INGRESS_ADAPTER_OPEN` |
| OTH-26 | `V4-BCA-R2-f50330e115a40dfbb290` | `src/workbench_service/core_product_bff_r1.py:673`<br>`identity_records` | `read_bytes`<br>`self.api.root/'data/v4/V4_DATA_ACCEPTED_HEAD.json'` | V4-NCFR-0160815, V4-NCFR-0160822 | `IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION` |
| OTH-27 | `V4-BCA-R2-74669f7b679e777ae31d` | `src/workbench_service/operational_daily_server_v1.py:54`<br>`do_GET` | `read_bytes`<br>`root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'` | V4-NCFR-0160917, V4-NCFR-0160924 | `OPEN` |
| OTH-28 | `V4-BCA-R2-2fdef93c69baedac776b` | `src/workbench_service/operational_daily_server_v1.py:88`<br>`do_GET` | `read_bytes`<br>`root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'` | V4-NCFR-0160921, V4-NCFR-0160928 | `OPEN` |

## Audit boundary and next work

This is a targeted mechanism review. It did not rerun R19/R20 whole-repository scans, call a market-data source, connect to PostgreSQL, perform DDL/DML, change an accepted Head, launch a service, or deploy to production. Local temporary evidence stayed under `G:\codex_tmp\r21`; only this concise formal review is intended for the Git history.

Next: crosswalk the 16 unmatched external-source rows; verify the eight remaining active ingress/publisher rows against their exact source bindings; finalize the per-dataset contract and capability gates; then migrate the 18 mutable Head/index reads and resolve the 10 contract/gate classifications. Recompute P1 only after source hashes and callsite identities reconcile. Keep the current count at 266 until that evidence is accepted.
