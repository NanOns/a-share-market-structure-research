-- M9-01 sector daily vector.  The existing 009/010 identities are legacy M8
-- nodes; this forward node is the canonical M9 cycle storage boundary.
CREATE TABLE sector_cycle_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    sector_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    sector_name VARCHAR NOT NULL,
    sector_type VARCHAR NOT NULL,
    history_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    board_quote_ret1 DOUBLE,
    board_quote_source VARCHAR,
    member_ret1_median DOUBLE,
    member_ret5_median DOUBLE,
    member_ret20_median DOUBLE,
    member_amount_sum DECIMAL(24, 2),
    amount_valid_count BIGINT NOT NULL,
    total_member_count BIGINT NOT NULL,
    quote_valid_count BIGINT NOT NULL,
    factor_valid_count BIGINT NOT NULL,
    coverage DOUBLE,
    breadth_ret1 DOUBLE,
    breadth_ma20 DOUBLE,
    sector_rs5 DOUBLE,
    sector_rs20 DOUBLE,
    sector_rs5_pct DOUBLE,
    sector_rs20_pct DOUBLE,
    amount_vs_prior20 DOUBLE,
    rank DOUBLE,
    rank_change DOUBLE,
    window_stats JSON NOT NULL,
    PRIMARY KEY (slice_id, sector_id, trade_date)
);
CREATE INDEX sector_cycle_daily_date_idx ON sector_cycle_daily (slice_id, trade_date, sector_type, sector_id);
