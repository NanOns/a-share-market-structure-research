# V4-01 TDX History Bootstrap — Stage Receipt

## Contract and authorization

| Field | Record |
|---|---|
| Stage | `V4-01 / TDX History Bootstrap` |
| Stage contract | V4.2.2 REV2 §§3B.1–3B.6 and §78; `V4_TDX_HISTORY_BOOTSTRAP_V1` |
| Machine contract | [v4_01_bootstrap_contract_v1.json](../config/v4_01_bootstrap_contract_v1.json) |
| Phase 0 | `DEGRADED_PASS` |
| Entry permission | `AUTHORIZED` by the R4 external Phase 0 seal; RAW Bootstrap only |
| Scanner permission | `NOT_APPLICABLE_UNTIL_V4_05` |
| Stage result | `DEGRADED_PASS` |
| Next stage | `V4-02 / Canonical Daily / PIT Periods`, with unresolved PIT and adjusted scopes still fail-closed |

The current stage used the read-only source boundary `D:/new_tdx`. Project artifacts and the retained raw package are under the project root. No database writes, scanner or factor execution, adjustment synthesis, or request for a fresh package occurred.

## Source package and official page observation

The already sealed source bundle `6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2` supplied the 2026-09-24 `hsjday.zip` package. The package is retained by content hash at:

`data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip`

The SHA-256 is `b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f` (550,821,395 bytes). It has 12,438 ZIP entries; CRC validation passed. The copy was made atomically, verified against the source hash, and marked read-only. Its 12,438 daily files expand to 952,586,848 bytes and contain 29,768,339 records.

The official page was observed at 2026-09-25 08:27:38 UTC. Its update-date field was blank. The page says the full package contains Shanghai, Shenzhen and Beijing daily data across several asset classes, and says to wait until the displayed update date matches the current day before downloading same-day data. The page observation is archived at `docs/evidence/V4_01_OFFICIAL_SOURCE_PAGE_OBSERVATION_20260925.json`, SHA-256 `a30ff5260232c714115e6959beb345975df64102a930b269434e4fcd97ab536f`. Therefore this stage reused the already sealed 2026-09-24 package and performed zero new downloads. The reused package's original transfer start/finish timestamps were unavailable and are recorded as unknown rather than reconstructed.

## History and overlap evidence

The parser retained and profiled every `.day` file without filtering the archive through the current research universe. It produced 12,438 inventory rows covering 1990-12-19 through 2026-09-24. The inventory's security-type hint is descriptive as of the captured metadata only; it does not establish historical lifecycle or PIT membership.

The archive contains 486 observed market sessions in the two-year window 2024-09-25 through 2026-09-24. The broad-market index chain has 8,247 sessions before that window; the latest 300-session warm-up begins 2023-07-04. This is market-calendar coverage only. Each security's observed bar start and end remain in the inventory so later stages can calculate field-level availability.

The V4-00D accepted A-stock overlap evidence was reused without rerunning 00D: 60 sessions (2026-07-03 through 2026-09-24), 265,993 comparable rows, 263,554 exact rows, 2,439 accepted normalized/source-refresh rows, zero unexplained mismatches, and zero filename-key identity mismatches. Evidence is in `reports/v4_00d/v4_00d_asset_stratified_postcheck_20260925.json`; V4-01 records its SHA-256 in the machine source manifest.

## Scoped limitations

The full raw archive was preserved, but the package's presence or missing bars do not establish listing, suspension, delisting, ST, or historical research-universe membership. All inventory rows therefore use `DIAGNOSTIC_NON_PIT`; lifecycle status remains unknown absent versioned dated facts. No PIT membership facts were fabricated.

Eighteen daily files contain validation exceptions, all outside the current A-stock class from the captured metadata: five index files (one has a non-increasing date), one convertible-bond file, six sector/market-index-like files, four B-share files, and two empty other-asset files. One extra retained ZIP entry has a nonnumeric TDX filename (`sz200b07.day`) and cannot be assigned a security identity. No file was discarded from the raw archive or inventory; current A-stock validation reports zero invalid files. These non-core and unidentifiable entries are scoped for downstream exclusion/diagnostic handling.

Adjusted history is not certified by this raw archive. Unsupported corporate-action categories remain fail-closed, and adjusted empirical coverage remains deferred under the Phase 0 limitations. Existing independent contract audits V422-B01/B03/B04/B07/B08/B10 and `AUD-AMOUNT-A-06` remain open and independent; this stage does not close or broaden them.

## Acceptance and evidence paths

**Acceptance:** `DEGRADED_PASS`. The immutable package hash and ZIP CRC, full daily-file inventory, current A-stock source validation, and accepted 60-session A-stock overlap evidence pass. Historical PIT/lifecycle facts, fresh page-date readiness, original transfer timestamps, non-core file anomalies, and adjusted-price availability remain scoped limitations.

Machine evidence:

- `reports/v4_01/v4_01_stage_receipt_20260925.json`
- `reports/v4_01/v4_01_source_manifest_20260925.json`
- `reports/v4_01/v4_01_security_inventory_20260925.csv`
- `docs/evidence/V4_01_OFFICIAL_SOURCE_PAGE_OBSERVATION_20260925.json`
- Immutable archive: `data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip`

The project artifacts were written atomically outside the TDX root. This stage did not write canonical daily tables, adjusted history, scanner results, factors, or production state; V4-02 owns Canonical Daily / PIT Periods.
