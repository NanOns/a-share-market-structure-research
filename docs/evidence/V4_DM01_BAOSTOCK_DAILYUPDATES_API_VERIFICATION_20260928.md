# DM-01 BaoStock DailyUpdates API verification

Date: 2026-09-28

Stage contract: V4_CONTINUOUS_DATA_MAINTENANCE_V2 and V4_DAILY_SOURCE_FREEZE_V2.

## Official API evidence

The official BaoStock Knowledge Base exposes the DailyUpdates article and describes date-specific A-share/ETF daily K lines and adjustment factors:

- Knowledge Base: https://www.baostock.com/helpDocsHome
- DailyUpdates article: https://www.baostock.com/mainContent?file=DailyUpdates.md

The article's API examples and the installed SDK source agree on these exact date-level batch calls:

| Operation | Exact SDK call | Request argument | Verified response fields |
|---|---|---|---|
| All-stock daily K | query_daily_history_k_AStock(date=...) | Exact YYYY-MM-DD date | date, code, OHLC, preclose, volume, amount, adjustflag, turn, tradestatus, pctChg, valuation fields, isST |
| Daily adjustment-factor batch | query_daily_adjust_factor(date=...) | Exact YYYY-MM-DD date | code, dividOperateDate, foreAdjustFactor, backAdjustFactor, adjustFactor |

The installed SDK exposes both methods. Its query_daily_adjust_factor result carries the requested date separately from the row field dividOperateDate; the adapter verifies the result-level provider date and preserves the row field as returned. The SDK sets a 20,000-row page size for these date-level operations. DM-01 caps each operation at 20,000 rows and one page and routes calls through the existing serial BaoStockClient and RequestBudget.

## Runtime and acceptance boundary

The repository's verified public runtime pin remains baostock==0.9.3; the current workspace interpreter has 0.9.4. The adapter rejects the public 0.9.4 runtime before issuing a data request. The independent V4-00F BaoStock acceptance audit remains OPEN; its latest bounded API-key evidence recorded provider error 10001015 for data queries. Therefore the API shape is verified, but no current-session BaoStock payload is accepted by this evidence.

DM-01 retains the task's required WAIT_BAOSTOCK_DAILY_UPDATE behavior when date-exact daily K and adjustment-factor snapshots are not available. BaoStock OHLC does not replace TDX raw data, and BaoStock adjustment factors do not replace the accepted QFQ chain.

## Verification artifacts

- Current installed SDK API source: E:/python/Lib/site-packages/baostock/security/history.py and E:/python/Lib/site-packages/baostock/evaluation/season_index.py (read-only; not copied into the repository).
- Adapter: src/workbench_analysis/baostock_daily_update_source.py.
- Runtime pin and prior source acceptance: requirements-v4-baostock.txt, config/baostock_supplemental_contract_v1.json, and docs/audits/V4_00F_BAOSTOCK_GATE_AUDIT_20260925.md.
- Required dataset acceptance remains pending a bounded target-date response, provider-date check, immutable rows/factor snapshot, and independent audit closure.
