-- M13B-02 / 021_m13_limit_promotion
-- Descriptive promotion counts derived only from materialized M13B-01 ladder rows.
CREATE TABLE limit_promotion_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    previous_trade_date DATE NOT NULL,
    trade_date DATE NOT NULL,
    previous_level VARCHAR NOT NULL CHECK (previous_level IN ('1', '2', '3', '4PLUS')),
    previous_up_count BIGINT NOT NULL,
    previous_unconfirmed_count BIGINT NOT NULL,
    success_count BIGINT NOT NULL,
    eligible_count BIGINT NOT NULL,
    excluded_unknown BIGINT NOT NULL,
    excluded_suspended BIGINT NOT NULL,
    excluded_no_limit BIGINT NOT NULL,
    rate DOUBLE,
    contract_id VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, trade_date, previous_level)
);

CREATE INDEX limit_promotion_daily_date_idx
    ON limit_promotion_daily (slice_id, trade_date, previous_level);
