-- M9-03 candidate, confirmation and stale representative state.
CREATE TABLE representative_state_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    sector_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    ranked_first_id VARCHAR,
    ranked_second_id VARCHAR,
    rank_gap DOUBLE,
    confirmed_id VARCHAR,
    candidate_id VARCHAR,
    candidate_since DATE,
    candidate_streak BIGINT NOT NULL,
    confirmed_since DATE,
    confirmation_event VARCHAR,
    previous_confirmed_id VARCHAR,
    stale BOOLEAN NOT NULL,
    representative_rank_basis VARCHAR NOT NULL,
    history_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, sector_id, trade_date)
);
CREATE INDEX representative_state_daily_date_idx ON representative_state_daily (slice_id, trade_date, sector_id);
