# V4-02 Canonical Daily / PIT Periods — Stage Receipt

## Contract and stage entry

| Field | Record |
|---|---|
| Stage | `V4-02 / Canonical Daily / PIT Periods` |
| Governing contract | V4.2.2 REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`; §§3B.6, 3C.1–3C.4, 5.2–5.3, 6A, 10N, 78 |
| Machine contract | [v4_02_canonical_daily_pit_contract_v1.json](../config/v4_02_canonical_daily_pit_contract_v1.json), `V4_CANONICAL_DAILY_PIT_PERIODS_V1` |
| Entry gate | Phase 0 `DEGRADED_PASS`; V4-01 `DEGRADED_PASS`; raw package SHA-bound |
| Stage result | `DEGRADED_PASS` |
| Next stage | `V4-03 / Pure-Core Factors`; proceed only for contract-ready RAW capabilities, while PIT, adjusted and limit-dependent paths remain closed |

The stage consumed the V4-01 retained 2026-09-24 package and its extracted project snapshot. `D:/new_tdx` and all configured live TDX roots were not read or written in this stage. No database writes, downloads, scanner runs, factor runs or trading actions occurred.

## Output contract

The processor writes every record from all 12,438 profiled `.day` files into the RAW canonical Parquet dataset, including rows from files with validation issues and the unclassifiable filename. It binds each row to its source file and record ordinal, retains TDX integer prices and source-native amount/volume, and attaches record validation, current metadata type hint, diagnostic membership and `limit_status=UNKNOWN`. Current metadata is descriptive only and never filters the input universe.

Weekly and monthly values are derived only from accepted actual OHLC records in the retained Daily source. Open is the first bar in date/record order, high/low are extrema, close is the last bar, and amount/volume are source-native sums. The local package's index bar dates provide a **diagnostic calendar proxy**, not an official exchange calendar. Rows distinguish a calendar period that had ended by T0 from an in-progress period, but they are labelled `DIAGNOSTIC_CLOSED_PERIOD` / `DIAGNOSTIC_AS_OF_PARTIAL`; this stage cannot prove the completeness needed for formal `CLOSED_ONLY`.

Each period row records `calendar_count`, unique `actual_count`, `max_source_trade_date`, `asof_trade_date`, raw adjustment view, `DIAGNOSTIC_NON_PIT` lineage, and unknown coverage cause. `suspended_count` remains null. Missing bars do not imply suspension or delisting. Historical adjustment, AS_RECORDED consumed-source revisions, lifecycle/PIT membership, historical limit rules and ex-right reference prices remain unavailable; daily and period `limit_status` is `UNKNOWN`.

The default cutoff is `2026-09-24`, the frozen package's last session. The processor accepts a bounded `--asof YYYYMMDD` no later than the package cutoff and filters source records at or before T0 before period aggregation. This is a deterministic implementation boundary, but it does not establish the REV2 §3C.4 multi-boundary/truncation acceptance suite; `PERIOD_ASOF_V1` temporal-leakage acceptance remains open.

## Evidence and acceptance

Machine artifacts:

- Stage processor: [v4_02_canonical_daily_pit.py](../scripts/v4_02_canonical_daily_pit.py)
- Stage receipt: `reports/v4_02/{run_id}_stage_receipt.json`
- Source manifest: `reports/v4_02/{run_id}_source_manifest.json`
- RAW Daily canonical and diagnostic periods: `data/v4/canonical/{run_id}/`

Completed run: `V4_02_CANONICAL_DAILY_PIT_20260924_085207Z`. It processed all 12,438 files and retained all 29,768,339 input records; 425 records carry a non-normal quality flag and remain in the RAW table. It emitted 6,297,060 weekly and 1,498,972 monthly diagnostic rows. A post-write check matched Parquet metadata row counts to the stage receipt, matched each output's byte count and SHA-256, and matched the source manifest's receipt digest.

Exact machine artifacts:

- [Stage receipt](../reports/v4_02/V4_02_CANONICAL_DAILY_PIT_20260924_085207Z_stage_receipt.json)
- [Source manifest](../reports/v4_02/V4_02_CANONICAL_DAILY_PIT_20260924_085207Z_source_manifest.json)
- [RAW canonical and period Parquet directory](../data/v4/canonical/V4_02_CANONICAL_DAILY_PIT_20260924_085207Z/)

The machine receipt records actual row counts, hashes, file sizes, calendar proxy coverage, source identities and a digest for each output. The accepted scope is full-retention RAW canonicalization plus diagnostic period aggregation. **Acceptance is `DEGRADED_PASS`**, because complete exchange-calendar and suspension evidence, historical identity/PIT, adjusted coordinates, historical price-limit rules, and the §3C.4 temporal-leakage scenarios are not accepted.

V422-B01, B03, B04, B07, B08, B10, and `AUD-AMOUNT-A-06` remain separate OPEN audit items. This stage does not close or re-scope them.
