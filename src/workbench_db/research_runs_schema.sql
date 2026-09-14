CREATE TABLE IF NOT EXISTS research_runs (
    run_id VARCHAR PRIMARY KEY, input_key VARCHAR UNIQUE NOT NULL, trade_date DATE NOT NULL,
    publication_id VARCHAR NOT NULL, snapshot_id VARCHAR NOT NULL, membership_snapshot_id VARCHAR NOT NULL,
    algorithm_version VARCHAR NOT NULL, parameter_hash VARCHAR NOT NULL, dependency_bindings JSON NOT NULL,
    history_basis VARCHAR NOT NULL, status VARCHAR NOT NULL, created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP, error_code VARCHAR,
    CHECK (status IN ('BUILDING','COMPLETE','FAILED'))
);
CREATE TABLE IF NOT EXISTS research_stock_states (
    run_id VARCHAR NOT NULL, security_id VARCHAR NOT NULL, setup BOOLEAN, breakout BOOLEAN, recovery BOOLEAN,
    trend_background BOOLEAN, structure_break BOOLEAN, quality VARCHAR NOT NULL, bias20 DOUBLE, sigma20 DOUBLE,
    extension_z20 DOUBLE, dist_high20 DOUBLE, range5 DOUBLE, range20 DOUBLE, rps5_delta3 DOUBLE,
    liquidity20_amount DOUBLE, risk_codes JSON NOT NULL, reason_codes JSON NOT NULL, evidence JSON NOT NULL,
    PRIMARY KEY (run_id, security_id)
);
CREATE TABLE IF NOT EXISTS research_sector_states (
    run_id VARCHAR NOT NULL, sector_id VARCHAR NOT NULL, current_eligible BOOLEAN, potential_eligible BOOLEAN,
    potential_branch VARCHAR, potential_branches JSON NOT NULL, current_rank INTEGER, potential_rank INTEGER,
    m1 DOUBLE, b1 DOUBLE, rel1 DOUBLE, p1 DOUBLE, q5 DOUBLE, q20 DOUBLE, dq5_3 DOUBLE, b_delta3 DOUBLE,
    ma20_width DOUBLE, ma20_delta3 DOUBLE, early_width DOUBLE, amount_a DOUBLE, top1_positive_share DOUBLE,
    member_count INTEGER, quote_valid_count INTEGER, feature_valid_count INTEGER, early_count INTEGER,
    positive_count INTEGER, quote_coverage DOUBLE, feature_coverage DOUBLE, risk_coverage DOUBLE,
    quality VARCHAR NOT NULL, reason_codes JSON NOT NULL, evidence JSON NOT NULL, input_members_hash VARCHAR,
    rank_universe_hash VARCHAR, PRIMARY KEY (run_id, sector_id)
);
CREATE TABLE IF NOT EXISTS research_sector_signal_state (
    run_id VARCHAR NOT NULL, sector_id VARCHAR NOT NULL, episode_id VARCHAR, first_seen_date DATE,
    last_qualified_date DATE, end_date DATE, age_sessions INTEGER, miss_sessions INTEGER, reset_sessions INTEGER,
    lifecycle VARCHAR, end_reason VARCHAR, prior_run_id VARCHAR, history_complete BOOLEAN NOT NULL,
    PRIMARY KEY (run_id, sector_id)
);
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
CREATE TABLE IF NOT EXISTS research_sector_member_roles (
    run_id VARCHAR NOT NULL, sector_id VARCHAR NOT NULL, security_id VARCHAR NOT NULL, role VARCHAR NOT NULL,
    role_rank INTEGER NOT NULL, today_rank INTEGER, role_reason_codes JSON NOT NULL, evidence JSON NOT NULL,
    PRIMARY KEY (run_id, sector_id, security_id, role)
);
CREATE TABLE IF NOT EXISTS research_shortlist (
    run_id VARCHAR NOT NULL, list_type VARCHAR NOT NULL, security_id VARCHAR NOT NULL, rank INTEGER NOT NULL,
    primary_sector_id VARCHAR, alternative_sector_ids JSON NOT NULL, selection_reason JSON NOT NULL,
    waiting_for JSON NOT NULL, invalid_if JSON NOT NULL, previous_state VARCHAR, change_reason VARCHAR,
    signal_date DATE,
    PRIMARY KEY (run_id, list_type, security_id), UNIQUE (run_id, list_type, rank),
    CHECK (list_type IN ('CURRENT_FOCUS','EARLY_FOCUS','INDIVIDUAL'))
);
ALTER TABLE research_shortlist ADD COLUMN IF NOT EXISTS signal_date DATE;
CREATE INDEX IF NOT EXISTS research_sector_states_current_idx ON research_sector_states(run_id, current_rank);
CREATE INDEX IF NOT EXISTS research_sector_states_potential_idx ON research_sector_states(run_id, potential_rank);
CREATE INDEX IF NOT EXISTS research_roles_lookup_idx ON research_sector_member_roles(run_id, sector_id, role, role_rank);
CREATE INDEX IF NOT EXISTS research_shortlist_lookup_idx ON research_shortlist(run_id, list_type, rank);
CREATE INDEX IF NOT EXISTS research_outcomes_lookup_idx ON research_signal_outcomes(signal_run_id, status, horizon);
