-- M10 mainline state.  All predicates remain auditable; no composite score is stored.
CREATE TABLE mainline_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    sector_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    sector_name VARCHAR NOT NULL,
    sector_type VARCHAR NOT NULL,
    mainline_class VARCHAR NOT NULL,
    previous_class VARCHAR,
    transition VARCHAR,
    observation_days BIGINT NOT NULL,
    valid_observation_days BIGINT NOT NULL,
    on_list_days JSON NOT NULL,
    consecutive_on_list BIGINT,
    current_percentile DOUBLE,
    current_breadth DOUBLE,
    current_amount_vs_prior20 DOUBLE,
    percentile_change_3d DOUBLE,
    breadth_change_3d DOUBLE,
    amount_change_3d DOUBLE,
    retention_rate DOUBLE,
    entered_count BIGINT,
    exited_count BIGINT,
    predicates JSON NOT NULL,
    missing_fields JSON NOT NULL,
    conflict_resolution VARCHAR,
    history_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, sector_id, trade_date)
);

CREATE INDEX mainline_daily_date_idx
    ON mainline_daily (slice_id, trade_date, sector_type, mainline_class, sector_id);
