-- M8A-01 / 008_technical_history
-- Immutable per-slice technical factors. Cross-sectional RPS and high
-- states are intentionally nullable until M8A-02; no placeholder values.
CREATE TABLE stock_technical_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    contract_id VARCHAR NOT NULL,
    price_basis VARCHAR NOT NULL,
    raw_close DOUBLE,
    adj_close DOUBLE,
    quote_ret1 DOUBLE,
    raw_amount DOUBLE,
    raw_volume DOUBLE,
    ma5 DOUBLE,
    ma10 DOUBLE,
    ma20 DOUBLE,
    ma60 DOUBLE,
    ret5 DOUBLE,
    ret10 DOUBLE,
    ret20 DOUBLE,
    ret60 DOUBLE,
    rs5 DOUBLE,
    rs10 DOUBLE,
    rs20 DOUBLE,
    rs60 DOUBLE,
    amount_ma5 DOUBLE,
    amount_ma10 DOUBLE,
    amount_ma20 DOUBLE,
    amount_ratio20 DOUBLE,
    amount_vs_prior20 DOUBLE,
    volume_vs_prior20 DOUBLE,
    amount_class VARCHAR,
    ma_alignment VARCHAR,
    validity VARCHAR NOT NULL,
    quality_codes JSON NOT NULL,
    basis_json JSON NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date)
);

CREATE INDEX stock_technical_daily_date_idx
    ON stock_technical_daily (slice_id, trade_date, security_id);
