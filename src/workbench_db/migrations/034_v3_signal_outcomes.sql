-- P10-03: outcome observations are append/update-only facts separate from
-- immutable research signal state rows.
CREATE TABLE IF NOT EXISTS research_signal_outcomes (
    signal_run_id VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    horizon INTEGER NOT NULL,
    eval_version VARCHAR NOT NULL,
    episode_id VARCHAR,
    due_date DATE,
    evaluated_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    confirmed_date DATE,
    confirmed_within_h BOOLEAN,
    lead_sessions INTEGER,
    member_forward_median DOUBLE,
    member_forward_coverage DOUBLE,
    evaluation_basis VARCHAR NOT NULL,
    evidence JSON NOT NULL,
    PRIMARY KEY (signal_run_id, sector_id, horizon, eval_version),
    CHECK (horizon IN (3, 5)),
    CHECK (status IN ('PENDING', 'OBSERVED', 'DATA_GAP')),
    CHECK (evaluation_basis IN ('HISTORICAL_RECONSTRUCTED', 'REAL_FORWARD'))
);
CREATE INDEX IF NOT EXISTS research_outcomes_lookup_idx ON research_signal_outcomes(signal_run_id, status, horizon);
