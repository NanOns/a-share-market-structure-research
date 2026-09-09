-- M8 contract completion / canonical 008 compatibility node.
-- Legacy 009_sector_base_history and 010_historical_structure remain immutable
-- migration identities; future M9/M10 migrations depend on this completion node.

CREATE TABLE market_reference_daily_v2 (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    quote_prev_close DECIMAL(18, 4),
    limit_up_price DECIMAL(18, 4),
    limit_down_price DECIMAL(18, 4),
    float_shares DOUBLE,
    shares_basis VARCHAR,
    status_known BOOLEAN NOT NULL,
    rule_id VARCHAR,
    source_ref VARCHAR,
    observed_at TIMESTAMP,
    contract_id VARCHAR NOT NULL,
    quality_codes JSON NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date)
);

INSERT INTO market_reference_daily_v2
SELECT r.slice_id, r.security_id, s.trade_date, r.quote_prev_close,
       r.limit_up_price, r.limit_down_price, r.float_shares, r.shares_basis,
       r.status_known, r.rule_id, r.source_ref, r.observed_at,
       'REFERENCE_CAPABILITY_V1_0', '[]'
  FROM market_reference_daily r
  JOIN analysis_slices s USING (slice_id);

DROP TABLE market_reference_daily;
ALTER TABLE market_reference_daily_v2 RENAME TO market_reference_daily;
CREATE INDEX market_reference_daily_date_idx
    ON market_reference_daily (slice_id, trade_date, security_id);

CREATE TABLE historical_coverage_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    trade_date DATE NOT NULL,
    contract_id VARCHAR NOT NULL,
    history_basis VARCHAR NOT NULL,
    real_observation BOOLEAN NOT NULL,
    observation_compatible BOOLEAN NOT NULL,
    membership_basis VARCHAR NOT NULL,
    membership_observation_class VARCHAR NOT NULL,
    membership_snapshot_id VARCHAR,
    price_basis VARCHAR NOT NULL,
    expected_security_count BIGINT NOT NULL,
    technical_row_count BIGINT NOT NULL,
    quote_valid_count BIGINT NOT NULL,
    quote_coverage DOUBLE,
    factor_valid_count BIGINT NOT NULL,
    factor_coverage DOUBLE,
    member_count BIGINT NOT NULL,
    member_sector_count BIGINT NOT NULL,
    membership_capability VARCHAR NOT NULL,
    structure_capability VARCHAR NOT NULL,
    structure_known_row_count BIGINT NOT NULL,
    structure_unknown_row_count BIGINT NOT NULL,
    structure_unique_hit_security_count BIGINT NOT NULL,
    queue_hit_counts_json JSON NOT NULL,
    quality_codes JSON NOT NULL,
    PRIMARY KEY (slice_id, trade_date)
);

CREATE INDEX historical_coverage_daily_date_idx
    ON historical_coverage_daily (slice_id, trade_date);
