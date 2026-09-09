-- M8A-02 / technical high and cross-sectional RPS state.
-- These tables are separate from M8A-01 so RPS/high semantics cannot
-- overwrite the first-step technical factor contract.
CREATE TABLE stock_high_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    "window" INTEGER NOT NULL CHECK ("window" IN (20, 30, 60, 100)),
    contract_id VARCHAR NOT NULL,
    price_basis VARCHAR NOT NULL,
    prior_max_close DOUBLE,
    new_high BOOLEAN,
    at_prior_high BOOLEAN,
    streak INTEGER,
    is_left_censored BOOLEAN NOT NULL,
    dist_prior_high DOUBLE,
    valid_n INTEGER NOT NULL,
    quality_codes JSON NOT NULL,
    basis_json JSON NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date, "window")
);

CREATE INDEX stock_high_daily_lookup_idx
    ON stock_high_daily (slice_id, trade_date, "window", security_id);

CREATE TABLE stock_strength_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    contract_id VARCHAR NOT NULL,
    price_basis VARCHAR NOT NULL,
    ret5 DOUBLE,
    ret10 DOUBLE,
    ret20 DOUBLE,
    ret60 DOUBLE,
    rs5 DOUBLE,
    rs10 DOUBLE,
    rs20 DOUBLE,
    rs60 DOUBLE,
    rps5 DOUBLE,
    rps10 DOUBLE,
    rps20 DOUBLE,
    rps60 DOUBLE,
    rps_valid_universe_count5 INTEGER NOT NULL,
    rps_valid_universe_count10 INTEGER NOT NULL,
    rps_valid_universe_count20 INTEGER NOT NULL,
    rps_valid_universe_count60 INTEGER NOT NULL,
    quality_codes JSON NOT NULL,
    basis_json JSON NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date)
);

CREATE INDEX stock_strength_daily_lookup_idx
    ON stock_strength_daily (slice_id, trade_date, security_id);
