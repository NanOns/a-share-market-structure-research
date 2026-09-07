# Phase1 Normalized Physical Contract V1

Extends adjusted-daily-contract-v0.3 without modifying its frozen document.
Physical version: adjusted-daily-contract-v1. Canonical file: data/normalized/adjusted_daily.parquet.

raw/adj OHLC: decimal128(18,2), exact stored cents. qfq_mul/qfq_add: canonical base-10 Decimal strings, lossless serialization of the sealed engine's 40-significant-digit factors (not binary floats or cent-rounded coefficients). Parse using Decimal. date=date32, raw_volume=int64 shares, raw_amount=float64 from the original float32 amount, booleans and categorical strings.

The Phase1 task distinguishes price_basis=TDX_NATIVE_QFQ from project_price_basis=FORWARD_ADJUSTED; both columns are retained. Historical normalized records carry universe_asof_date=cutoff; that membership is not a historical eligibility claim. Actual raw bars are preserved; synthetic and other missing rows have NULL raw and adj OHLC and NULL A/B. aligned_close/aligned_volume/aligned_amount alone carry legal suspension fills. No synthetic adj_high/adj_low is invented. Missing-state classification is inherited from Phase0.1, using evidence known at the cutoff only.

Full history from first observed bar (or latest251-session context for a newer listing) through cutoff is calendar-aligned. Original raw observations outside the master calendar are preserved with OFF_MASTER_CALENDAR and is_master_session=false; they do not enter factor market-session windows. This retains early historical anomalies without silently altering the frozen master calendar. Missing source files produce FILE_MISSING context and are excluded from NORMAL_UNIVERSE. Current-membership A-stock identity and conservative fallback code rules are reused; current membership is never retrojected into historical factor rows.

Historical adjusted prices are a current-snapshot analytical series. Only factor rows at the current output cutoff are computed. Past factors require separately retained historical source/membership snapshots; historical --date is rejected. This distinction is necessary because ordinary QFQ history uses events after the historical bar up to the current anchor. The first build does not mislabel that as historical point-in-time data.

The engine reuses exact factors for event-constant date intervals. Vectorized cent conversion uses a conservative floating error band and falls back to the sealed Decimal qfq_price method near every half-cent boundary. No clipping, source edits or algorithm parameter changes are permitted.

Publication stages both files, validates, fsyncs and atomically replaces each, then publishes the final receipt. Consumers must validate receipt hashes/generation before reading the pair. Per-security cache is rebuildable and is never authoritative production data.
