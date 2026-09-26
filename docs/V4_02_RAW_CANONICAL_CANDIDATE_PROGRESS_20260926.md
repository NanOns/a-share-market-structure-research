# V4-02 RAW Canonical Candidate Progress (2026-09-26)

## Stage contract and evidence

- Stage: `V4-02 / Canonical Daily / PIT Periods`.
- Governing upgrade: `DA-MSR-V4.2.2-CODEX-REV2`, SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`; §§3B.6, 3C.1–3C.4, 5.2–5.3, 6A, 10N, 78.
- Machine contract: `V4_CANONICAL_DAILY_PIT_PERIODS_V2`; field-level map: `V4_02_STAGE_ACCEPTANCE_MAPPING_V1`.
- Entry gate: [V4-02 entry receipt](../reports/v4_02/V4_02_ENTRY_GATE_20260926.json), `ENTRY_AUTHORIZED`, 11/11 checks passed. The gate confirms authority to start; it does not accept V4-02 data capabilities.
- Input basis: V4-01 R6.2 externally accepted required scope, the R4 accepted source-selection manifest, the 2026-09-24 ZIP/extracted snapshot, and R6.2 membership interval facts. No configured TDX root was accessed or modified; the runner reports zero TDX-root reads/writes.

## RAW candidate delivered

Run: `V4_02_RAW_SELECTED_20260924_062040Z`.

The runner replayed all 22,853 R4 source-selection segments and matched the accepted selection digest. It verified the ZIP and extracted files, the local snapshot, the R4 source manifest, and the R6.2 membership interval artifact before writing. Source selection covers 29,690,462 rows. It excluded 469,552 Beijing Exchange rows from the required output and counted them separately under the optional degraded scope. The resulting required RAW Parquet contains 29,220,910 rows, with no BSE source key in that file.

Selected source counts are 29,126,072 local TDX rows and 94,838 complete-package gap-fill rows. All emitted rows retain `DIAGNOSTIC_NON_PIT` lineage and `limit_status=UNKNOWN`. Canonical security IDs are assigned only inside accepted R6.2 dated-roster intervals: 4,027,002 rows. The remaining 25,193,908 rows keep a null canonical ID and an explicit unresolved identity quality; no current-universe membership was projected backward.

Independent candidate postcheck: [postcheck receipt](../reports/v4_02/V4_02_RAW_SELECTED_20260924_062040Z_independent_postcheck.json), `CANDIDATE_POSTCHECK_PASS`, 9/9 checks. It read Parquet metadata and the full row stream, verified schema/row count/bytes/SHA-256 and fail-closed quality markers, confirmed BSE exclusion and the as-of cutoff, and reread bounded source-record samples (including overlapping alternatives) against the selected source files.

Output evidence:

- Stage receipt: [stage_receipt.json](../data/v4/canonical/V4_02_RAW_SELECTED_20260924_062040Z/stage_receipt.json), SHA-256 `b6b014081fd248af457c08147dc35721ff1e6e3aa5ad399b3c2fdb7b630144c6`.
- Source manifest: [source_manifest.json](../data/v4/canonical/V4_02_RAW_SELECTED_20260924_062040Z/source_manifest.json), SHA-256 `d337fe2c0cd4cb02f05262337b14f47c32a8fd72c2f35594ac00b5f2caf5de6b`.
- Parquet: [canonical_daily_raw_selected.parquet](../data/v4/canonical/V4_02_RAW_SELECTED_20260924_062040Z/canonical_daily_raw_selected.parquet), 29,220,910 rows, 1,988,198,932 bytes, SHA-256 `cdbc3e2b49bf16f59a6661d4641a3d9a3b498c5a9843974e934a7ab695f02313`.
- Source families and board counts are recorded in the postcheck report. The four required board scopes have rows; BSE has 0 emitted rows and 469,552 separately excluded rows.

An earlier candidate that mixed BSE rows into the shared output is retained with a `SUPERSEDED_CANDIDATE` disposition. A second candidate built against the pre-final machine-contract hash is also retained and marked superseded. Neither is used as current evidence.

## Acceptance result and remaining work

Current result: `RAW_SELECTED_CANDIDATE_POSTCHECK_PASS / V4-02 BLOCKED / STAGE NOT ACCEPTED`. The postcheck accepts artifact integrity and source selection for this RAW candidate only. It does not close the formal canonical identity scope, PIT knowledge lineage, adjusted data, exchange calendar, trading status, periods, price limits, or full-stage publication gates.

Open required capabilities:

- Complete dated identity/lifecycle coverage beyond the R6.2 roster-observed interval; historical source bars remain diagnostic and non-PIT.
- Adjusted canonical daily and periods under `TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1`; the V4-00E real-action acceptance audit remains OPEN.
- Formal versioned market calendars and dated trading/suspension/resumption facts. Missing bars remain unknown.
- Formal weekly/monthly `CLOSED_ONLY` and `AS_OF` outputs using accepted calendars and coverage facts.
- §3C.4 multi-boundary/truncation and future-row perturbation invariance acceptance.
- Dated official `PRICE_LIMIT_RULE_V1` rules, ex-right reference-price inputs, and independent historical samples.
- Independent acceptance of the full V4-02 publication set. The RAW-only candidate postcheck does not accept full-stage publication.

No generic degraded completion is allowed. BSE is the only optional degraded scope and is isolated from the required RAW artifact and digest. V4-03 remains blocked.

## Next stage

Continue V4-02 by implementing formal calendar and dated trading-status inputs, then adjusted price and formal period capabilities with their own versioned contracts and independent evidence. Re-run the whole-stage postcheck only after all required capabilities are present. Do not proceed to V4-03 before V4-02 acceptance.



## Official calendar source evidence update

On 2026-09-26, a bounded capture stored 10 official source pages (four exchange-rule pages and six annual closure notices for 2024–2026) under `data/v4/source_evidence/official_calendar_v1/capture_20260926T064500Z/`. The immutable capture manifest binds the frozen `V4_OFFICIAL_EXCHANGE_CALENDAR_V1` contract hash `b13211cf2b56cfedbf30f0cdab15566ed0322a347784eaa61e67b861fafdfbad`; it records HTTP 200 for all 10 pages and 282,286 total bytes. A local integrity pass confirmed all captured page byte counts and SHA-256 hashes match the manifest. The failed first request exposed a stale Shenzhen 2023 rule URL; the contract was corrected to the official `www.szse.cn` rule page before the successful capture.

This is source evidence only. No closure dates have yet been parsed into a calendar artifact, one-off amendments have not been exhaustively reviewed, and no session crosscheck or independent calendar acceptance has run. Calendar capability therefore remains `OFFICIAL_SOURCE_CANDIDATE_2024_2026_ONLY_NOT_FORMAL_ACCEPTED`; V4-02 remains blocked and V4-03 remains blocked. Next step: parse source pages into separate SSE/SZSE candidate calendars, bind manually reviewed expected dates, then crosscheck exchange sessions and as-of/future-notice boundaries.


## Candidate calendar build and crosscheck update

The manually transcribed expected closure ranges are bound to `V4_OFFICIAL_EXCHANGE_CALENDAR_EXPECTED_CLOSURES_V1`. Builder `scripts/build_v4_official_calendar_candidate.py` verified every cited phrase in the source pages and emitted separate SSE/SZSE calendar candidates for 2024-01-01 through 2026-12-31. Each candidate has 727 weekday sessions and 57 weekday closure dates (90 unique closure-calendar dates including weekends). The candidates remain reconstructed, not `PIT_OBSERVED`.

Diagnostic postcheck `reports/v4_02/V4_OFFICIAL_CALENDAR_CANDIDATE_POSTCHECK_20260926.json` verified the weekday partition and compared dates with the SH.000001 and SZ.399001 series from the accepted V4-01 R4 complete-package input. Both markets match exactly through 2026-09-24: 663 candidate sessions, 0 missing index dates, and 0 unexpected index dates. This is a package-index diagnostic, not an independent exchange calendar acceptance. The older local snapshot ends at 2026-09-10 for these indices, so its apparent 2026-09-11 discrepancy is a snapshot-coverage gap; the accepted R4 package contains that session and resolves it.

A supplemental, versioned source contract `V4_OFFICIAL_CALENDAR_AMENDMENTS_2026_V1` captured eight 2026 single-holiday SSE/SZSE notices published by 2026-09-26. All eight pages are hash-bound and their listed weekday closure ranges agree with the annual schedules. The official SZSE notice listing also shows a 2026 Dragon Boat closure notice, but its canonical notice-page URL remains unresolved and that page is not captured. This prevents claiming that all later applicable notices have been reviewed.

Calendar result remains `CANDIDATE_DIAGNOSTIC_CROSSCHECK_PASS_ACCEPTANCE_PENDING`; V4-02 remains blocked. Remaining calendar work: resolve and capture the SZSE Dragon Boat notice, inventory applicable one-off notices for the full 2024–2026 period, review as-of/future-notice boundaries, and obtain independent postcheck and formal acceptance.


## External audit execution update (2026-09-26)

The latest applicable V4.2.2 REV2 executable contract was consulted before the calendar close-out (SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`, §§3B.6, 3C.1–3C.4, 5.2–5.3, 6A, 10N, 78). The user-provided audit instruction file `V4_02_EXTERNAL_AUDIT_CALENDAR_SCOPE_AND_STAGE_STATUS_20260926.md` was read and bound by SHA-256 `3422d177d133dd9e454cd85f9aacaf9fd2a81fdfec52ff26646f963360ce9779`.

### Formal market calendar close-out

- The former V1 candidate remains historical evidence. New V2 contracts narrow coverage to the accepted warmup start `2023-07-04` through source cutoff `2026-09-24`; future dates beyond cutoff are absent.
- Two official 2023 annual closure notices were captured under the frozen two-request source contract. Their capture manifest SHA-256 is `905ec0cca1728fe1108f2487d94b432053107ca3e8dcb48b3983c3df3cf55d12`. The prior 2024–2026 rule and annual-notice capture manifest remains bound at `cae5540e0cdf67f8234993a20f8cb3c4f4d482e083f336c96d647b0e5ae973b6`.
- The V2 candidate is in `data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/`. It has separate SSE/SZSE calendars, 786 sessions per exchange, and 57 weekday closure dates per exchange. Expected closure phrases are checked against hash-bound official source pages by the builder.
- Independent postcheck `reports/v4_02/V4_OFFICIAL_CALENDAR_V2_INDEPENDENT_POSTCHECK_20260926.json` reports `FORMAL_MARKET_CALENDAR_PASS`. Both primary index series from the accepted V4-01 package match exactly: SSE 786/786 and SZSE 786/786; missing dates 0; unexpected dates 0. Weekday partitions pass, all required boards are mapped, the calendar ends at cutoff, and lineage remains reconstructed rather than `PIT_OBSERVED`.
- Formal acceptance receipt: `reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json`, SHA-256 `374bce8b108afbcd476d4136176b6468168a8ea0ed34ab710386d0552f14c9e9`. No one-off amendment search was expanded because the documented trigger (unexplained mismatch) was absent. Calendar work is closed at this accepted scope.

### Updated stage state and next stage

- Versioned machine contract `V4_CANONICAL_DAILY_PIT_PERIODS_V3` and mapping `V4_02_STAGE_ACCEPTANCE_MAPPING_V2` record the accepted calendar while retaining `V4-02 BLOCKED_OPEN`; V1/V2 historical contracts were not overwritten.
- V4-02 remains blocked by RAW formal acceptance, adjustment, dated trading status/suspension/resumption, formal periods and CLOSED_ONLY/AS_OF, §3C.4 proofs, price-limit authority/samples, and whole-stage atomic publication/postcheck. V4-03 remains blocked.
- Next stage is `ADJUSTED_CANONICAL_DAILY_REAL_ACTION_ACCEPTANCE`. The independent audit `docs/audits/V4_00E_ADJUSTMENT_ACCEPTANCE_AUDIT_20260925.md` remains OPEN. Its gates include V4-00D accepted source-package overlap, event-type expected-price samples plus no-action control, long suspension/resumption and recent-listing cases, category-15 impact classification, multi-cutoff determinism and future/revision leakage checks, and per-security fail-closed output. Existing current-GBBQ reconstruction and Phase 1 QFQ artifacts are diagnostic inputs only and do not satisfy these gates.
- Board scope remains `SH_MAIN`, `SZ_MAIN`, `CHINEXT`, `STAR`; BSE remains optional and isolated. No scanner/factor work starts before V4-02 acceptance.


### Adjustment empirical sample construction update

- Consulted the separate `V4-00E-REAL-ADJUSTMENT-ACCEPTANCE-01` audit before execution. The V4-00D report is scope-specific: its A_STOCK row records `ACCEPTED_SOURCE_PACKAGE`, 265,993 comparable rows over 60 sessions, zero unexplained mismatch rows, and zero keyed identity mismatches; other asset types and the all-assets 00D gate remain blocked. The diagnostic below is limited to this accepted A-stock source scope and does not close the broader 00D audit.
- Frozen sample contract: `config/v4_02_adjustment_empirical_sample_contract_v1.json`, SHA-256 `b319f1445a4933e7e4e166128e78b1289bcbaed36248dcbe51172c945dc0687b`. It binds the V4-01 source-package digest, V4-00D A-stock disposition, gbbq/map hashes, cutoff and current-snapshot non-PIT lineage.
- Diagnostic evidence: `reports/v4_02/V4_02_ADJUSTMENT_EMPIRICAL_SAMPLE_DIAGNOSTIC_20260926.json`, SHA-256 `7655ab660835e799c58bdc91c4f23fee485ab8d4fb6755cec67e580a886028ae`. It contains real cash-only, share-bonus/transfer-only, rights-only, combined-action and no-action-control samples. Each sample’s QFQ OHLC matches a separate Decimal calculation against the sealed affine engine.
- This verifies only the category-1 calculation path for selected examples. The four action samples have unresolved non-category-1 records and therefore remain `adjusted_quality=UNAVAILABLE_OTHER_CATEGORY_UNRESOLVED`; the no-action sample is diagnostic control only. All 91 category-15 records remain unresolved for price impact. Current snapshot reconstruction is not PIT.
- Acceptance result: `DIAGNOSTIC_SAMPLE_EVIDENCE_ONLY`; `ADJUSTED_CANONICAL_DAILY=UNAVAILABLE`. Remaining adjustment gates include authoritative impact classification of unsupported categories, category-15 decisions, long suspension/resumption and recent-listing cases, multi-cutoff determinism, future/late revision leakage, and independent V4-00E closure. V4-02 remains blocked. Next adjustment action: adjudicate unsupported category impact from source semantics, then produce fail-closed per-security dispositions before expanding samples.
