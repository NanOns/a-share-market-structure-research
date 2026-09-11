-- M13B-01 / 020_m13_limit_ladder
-- Ladder rows are immutable, date-keyed outputs of local M8C state evaluation.
CREATE TABLE limit_ladder_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    limit_state VARCHAR NOT NULL CHECK (limit_state IN ('UP', 'DOWN', 'NONE', 'UNKNOWN', 'NO_LIMIT', 'SUSPENDED')),
    reference_basis VARCHAR NOT NULL,
    rule_id VARCHAR,
    limit_up_price DECIMAL(18, 4),
    limit_down_price DECIMAL(18, 4),
    streak BIGINT,
    streak_known BOOLEAN NOT NULL,
    streak_min_known BIGINT,
    previous_state VARCHAR,
    previous_streak BIGINT,
    ladder_level VARCHAR,
    promotion_state VARCHAR NOT NULL,
    denominator_eligible BOOLEAN,
    exclusion_reason VARCHAR,
    association_ref VARCHAR,
    contract_id VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date)
);

CREATE INDEX limit_ladder_daily_date_idx
    ON limit_ladder_daily (slice_id, trade_date, ladder_level, limit_state, security_id);
