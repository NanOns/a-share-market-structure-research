-- P12-11: immutable V3.3 bundle registry and candidate rows.
-- The legacy research_runs model remains unchanged for compatibility.
CREATE TABLE IF NOT EXISTS research_runs_v3_3 (
    bundle_digest VARCHAR PRIMARY KEY,
    research_run_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    publication_id VARCHAR NOT NULL,
    snapshot_id VARCHAR NOT NULL,
    membership_snapshot_id VARCHAR NOT NULL,
    bundle_contract_id VARCHAR NOT NULL,
    parameter_hash VARCHAR NOT NULL,
    dependency_lock_hash VARCHAR NOT NULL,
    history_basis VARCHAR NOT NULL,
    result_count INTEGER NOT NULL,
    bundle_path VARCHAR NOT NULL,
    contracts JSON NOT NULL,
    status VARCHAR NOT NULL,
    registered_at TIMESTAMP NOT NULL,
    UNIQUE (research_run_id, bundle_digest),
    CHECK (status IN ('COMPLETE')),
    CHECK (result_count >= 0)
);

CREATE TABLE IF NOT EXISTS research_candidates_v3_3 (
    bundle_digest VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    security_name VARCHAR,
    primary_category VARCHAR,
    matched_categories JSON NOT NULL,
    category_rank INTEGER,
    category_score DOUBLE,
    rank_status VARCHAR NOT NULL,
    selection_mode VARCHAR,
    sector_support_status VARCHAR,
    risk_codes JSON NOT NULL,
    factor_evidence JSON NOT NULL,
    scanner_evidence JSON NOT NULL,
    result_payload JSON NOT NULL,
    PRIMARY KEY (bundle_digest, security_id)
);

CREATE INDEX IF NOT EXISTS research_runs_v3_3_date_idx
    ON research_runs_v3_3(trade_date, registered_at);
CREATE INDEX IF NOT EXISTS research_candidates_v3_3_rank_idx
    ON research_candidates_v3_3(bundle_digest, primary_category, category_rank);
