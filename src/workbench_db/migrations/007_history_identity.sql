-- M7B-01 / 007_history_identity
-- Management, identity, universe and reference tables only.  Historical rows
-- are populated by later work packages after their inputs are frozen.
CREATE TABLE analysis_slices (
    slice_id VARCHAR PRIMARY KEY,
    domain VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    contract_id VARCHAR NOT NULL,
    input_hash VARCHAR NOT NULL,
    dependency_hash VARCHAR NOT NULL,
    basis_json JSON NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    logical_hash VARCHAR NOT NULL,
    storage_kind VARCHAR NOT NULL CHECK (storage_kind IN ('DUCKDB', 'PARQUET')),
    storage_object_id VARCHAR,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE analysis_slice_dependencies (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    input_domain VARCHAR NOT NULL,
    input_date DATE NOT NULL,
    input_slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    PRIMARY KEY (slice_id, input_domain, input_date, input_slice_id)
);

CREATE TABLE analysis_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    cutoff_date DATE NOT NULL,
    query_start DATE NOT NULL,
    universe_contract VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    manifest_hash VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('PREPARED', 'SUCCESS', 'FAILED')),
    created_at TIMESTAMP NOT NULL,
    CHECK (query_start <= cutoff_date)
);

CREATE TABLE analysis_snapshot_entries (
    snapshot_id VARCHAR NOT NULL REFERENCES analysis_snapshots(snapshot_id),
    domain VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    PRIMARY KEY (snapshot_id, domain, trade_date)
);

CREATE TABLE publication_analysis_snapshots (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    domain VARCHAR NOT NULL CHECK (domain IN ('LOCAL_OBSERVED', 'LOCAL_RECONSTRUCTED')),
    snapshot_id VARCHAR NOT NULL REFERENCES analysis_snapshots(snapshot_id),
    bound_at TIMESTAMP NOT NULL,
    PRIMARY KEY (publication_id, domain)
);

CREATE TABLE analysis_daily_basis (
    slice_id VARCHAR PRIMARY KEY REFERENCES analysis_slices(slice_id),
    universe_basis VARCHAR NOT NULL,
    membership_snapshot_id VARCHAR,
    price_basis VARCHAR NOT NULL,
    adjustment_as_of DATE,
    source_observed_at TIMESTAMP,
    coverage DOUBLE CHECK (coverage IS NULL OR (coverage >= 0 AND coverage <= 1)),
    capabilities_json JSON NOT NULL
);

CREATE TABLE membership_snapshot_metadata (
    membership_snapshot_id VARCHAR PRIMARY KEY REFERENCES membership_snapshots(membership_snapshot_id),
    observed_at TIMESTAMP NOT NULL,
    source_effective_date DATE,
    source_freshness VARCHAR NOT NULL,
    source_hash VARCHAR NOT NULL,
    semantic_version VARCHAR NOT NULL
);

CREATE TABLE sector_semantic_versions (
    version_id VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    bucket VARCHAR NOT NULL,
    rule_id VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,
    valid_from DATE,
    observed_at TIMESTAMP NOT NULL,
    override BOOLEAN NOT NULL,
    source_id VARCHAR NOT NULL,
    PRIMARY KEY (version_id, sector_id)
);

CREATE TABLE security_metadata_versions (
    security_id VARCHAR NOT NULL,
    version_id VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    board VARCHAR,
    security_kind VARCHAR NOT NULL,
    listing_status VARCHAR NOT NULL,
    valid_from DATE,
    valid_to DATE,
    observed_at TIMESTAMP NOT NULL,
    source_id VARCHAR NOT NULL,
    source_ref VARCHAR NOT NULL,
    PRIMARY KEY (security_id, version_id),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE universe_state_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    display_eligible BOOLEAN NOT NULL,
    quote_eligible BOOLEAN NOT NULL,
    structure_eligible BOOLEAN NOT NULL,
    listing_state VARCHAR NOT NULL,
    exclusion_reason VARCHAR,
    metadata_version VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, security_id)
);

CREATE TABLE market_reference_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    quote_prev_close DECIMAL(18, 4),
    limit_up_price DECIMAL(18, 4),
    limit_down_price DECIMAL(18, 4),
    float_shares DOUBLE,
    shares_basis VARCHAR,
    status_known BOOLEAN NOT NULL,
    rule_id VARCHAR,
    source_ref VARCHAR,
    observed_at TIMESTAMP,
    PRIMARY KEY (slice_id, security_id)
);

CREATE TABLE limit_rule_versions (
    rule_id VARCHAR PRIMARY KEY,
    exchange VARCHAR NOT NULL,
    board VARCHAR NOT NULL,
    risk_status VARCHAR NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    limit_ratio DOUBLE,
    tick DECIMAL(18, 4) NOT NULL,
    rounding_mode VARCHAR NOT NULL,
    special_period_policy JSON NOT NULL,
    source_ref VARCHAR NOT NULL,
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE TABLE IF NOT EXISTS schema_migration_checks (
    version VARCHAR PRIMARY KEY,
    sql_sha256 VARCHAR NOT NULL,
    dependencies JSON NOT NULL,
    previous_manifest_hash VARCHAR NOT NULL,
    applied_at TIMESTAMP NOT NULL,
    receipt_id VARCHAR NOT NULL
);
