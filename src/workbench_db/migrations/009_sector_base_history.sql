-- M8B-01 / 009_sector_base_history
-- Historical sector-base rows are independent from formal current snapshots.
CREATE TABLE sector_base_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    sector_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    sector_name VARCHAR NOT NULL,
    sector_type VARCHAR NOT NULL,
    sector_role VARCHAR NOT NULL,
    bucket VARCHAR,
    sector_valid BOOLEAN NOT NULL,
    total_member_count BIGINT NOT NULL,
    quote_valid_count BIGINT NOT NULL,
    factor_valid_count BIGINT NOT NULL,
    coverage DOUBLE,
    sector_rs5 DOUBLE,
    sector_rs10 DOUBLE,
    sector_rs20 DOUBLE,
    sector_rs60 DOUBLE,
    sector_rs5_pct DOUBLE,
    sector_rs20_pct DOUBLE,
    display_rank BIGINT,
    base_pattern VARCHAR NOT NULL,
    base_predicates JSON NOT NULL,
    semantic_version VARCHAR NOT NULL,
    membership_snapshot_id VARCHAR NOT NULL,
    membership_basis VARCHAR NOT NULL,
    price_basis VARCHAR NOT NULL,
    history_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    quality_codes JSON NOT NULL,
    PRIMARY KEY (slice_id, sector_id, trade_date)
);

CREATE INDEX sector_base_daily_date_idx
    ON sector_base_daily (slice_id, trade_date, sector_id);
