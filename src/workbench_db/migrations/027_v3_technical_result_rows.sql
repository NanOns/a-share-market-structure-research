-- V3 P03-02 technical domain result rows.
-- The legacy table remains immutable as a compatibility source.  Production
-- technical reads resolve through technical_result_daily, which prefers the
-- result-object binding and only exposes an unbound legacy slice as a
-- fail-safe compatibility fallback.
CREATE TABLE IF NOT EXISTS technical_result_rows (
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
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
    PRIMARY KEY (result_object_id, security_id, trade_date)
);

CREATE INDEX IF NOT EXISTS technical_result_rows_lookup_idx
    ON technical_result_rows (result_object_id, trade_date, security_id);

CREATE OR REPLACE VIEW technical_result_daily AS
SELECT
    b.slice_id,
    b.result_object_id,
    t.* EXCLUDE (result_object_id)
/*
    t.trade_date,
    t.contract_id,
    t.price_basis,
    t.raw_close,
    t.adj_close,
    t.quote_ret1,
    t.raw_amount,
    t.raw_volume,
    t.ma5,
    t.ma10,
    t.ma20,
    t.ma60,
    t.ret5,
    t.ret10,
    t.ret20,
    t.ret60,
    t.rs5,
    t.rs10,
    t.rs20,
    t.rs60,
    t.amount_ma5,
    t.amount_ma10,
    t.amount_ma20,
    t.amount_ratio20,
    t.amount_vs_prior20,
    t.volume_vs_prior20,
    t.amount_class,
    t.ma_alignment,
    t.validity,
    t.quality_codes,
    t.basis_json */
FROM analysis_slice_result_bindings b
JOIN analysis_result_objects o
  ON o.result_object_id = b.result_object_id
 AND o.domain = 'technical'
JOIN technical_result_rows t
  ON t.result_object_id = b.result_object_id
UNION ALL
SELECT
    legacy.slice_id,
    CAST(NULL AS VARCHAR) AS result_object_id,
    legacy.* EXCLUDE (slice_id)
/*
    legacy.trade_date,
    legacy.contract_id,
    legacy.price_basis,
    legacy.raw_close,
    legacy.adj_close,
    legacy.quote_ret1,
    legacy.raw_amount,
    legacy.raw_volume,
    legacy.ma5,
    legacy.ma10,
    legacy.ma20,
    legacy.ma60,
    legacy.ret5,
    legacy.ret10,
    legacy.ret20,
    legacy.ret60,
    legacy.rs5,
    legacy.rs10,
    legacy.rs20,
    legacy.rs60,
    legacy.amount_ma5,
    legacy.amount_ma10,
    legacy.amount_ma20,
    legacy.amount_vs_prior20,
    legacy.volume_vs_prior20,
    legacy.amount_class,
    legacy.ma_alignment,
    legacy.validity,
    legacy.quality_codes,
    legacy.basis_json */
FROM stock_technical_daily legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM analysis_slice_result_bindings bound
    WHERE bound.slice_id = legacy.slice_id
);
