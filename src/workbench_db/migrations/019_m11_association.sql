-- M11-03 association precompute.
-- One row is retained for every A-share membership candidate so rejected
-- relations remain explainable through API28 when explicitly requested.
CREATE TABLE stock_sector_associations_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    sector_name VARCHAR NOT NULL,
    sector_type VARCHAR NOT NULL,
    semantic_bucket VARCHAR NOT NULL,
    association_rank BIGINT,
    eligible BOOLEAN NOT NULL,
    rejection_reasons JSON NOT NULL,
    pattern VARCHAR,
    member_rank DOUBLE,
    member_rank_valid_count BIGINT,
    member_percentile DOUBLE,
    sector_coverage DOUBLE,
    sector_rs5_pct DOUBLE,
    sector_rs20_pct DOUBLE,
    loo_ret20_median DOUBLE,
    loo_breadth20 DOUBLE,
    loo_ret5_median DOUBLE,
    loo_breadth5 DOUBLE,
    evidence_json JSON NOT NULL,
    contract_id VARCHAR NOT NULL,
    history_basis VARCHAR NOT NULL,
    membership_snapshot_id VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, security_id, sector_id, trade_date)
);

CREATE INDEX stock_sector_associations_daily_security_idx
    ON stock_sector_associations_daily (slice_id, trade_date, security_id, eligible, association_rank);

CREATE INDEX stock_sector_associations_daily_sector_idx
    ON stock_sector_associations_daily (slice_id, trade_date, sector_id, security_id);
