-- M13A / 022_m13_market_cycle
-- Immutable, one-date market aggregation.  Empty-but-known dates remain
-- representable through row_count=0 and the capability/coverage JSON.
CREATE TABLE market_cycle_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    universe_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    contract_id VARCHAR NOT NULL,
    display_count BIGINT NOT NULL,
    quote_valid_count BIGINT NOT NULL,
    up_count BIGINT NOT NULL,
    down_count BIGINT NOT NULL,
    flat_count BIGINT NOT NULL,
    amount_sum DOUBLE,
    amount_valid_count BIGINT NOT NULL,
    ma20_above_count BIGINT NOT NULL,
    ma20_valid_count BIGINT NOT NULL,
    ma60_above_count BIGINT NOT NULL,
    ma60_valid_count BIGINT NOT NULL,
    new_high_counts JSON NOT NULL,
    queue_counts JSON NOT NULL,
    queue_unique_count BIGINT,
    sector_state_counts JSON,
    limit_up_count BIGINT,
    limit_down_count BIGINT,
    unknown_limit_count BIGINT,
    field_coverage JSON NOT NULL,
    capabilities JSON NOT NULL,
    PRIMARY KEY (slice_id)
);

CREATE INDEX market_cycle_daily_date_idx
    ON market_cycle_daily (slice_id, trade_date);
