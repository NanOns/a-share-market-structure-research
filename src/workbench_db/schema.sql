CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR PRIMARY KEY,
    applied_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
    publication_id VARCHAR PRIMARY KEY,
    trade_date DATE NOT NULL,
    revision INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    source_revision_id INTEGER,
    production_version VARCHAR,
    source_manifest_sha256 VARCHAR,
    source_identity_sha256 VARCHAR,
    computation_identity_sha256 VARCHAR,
    render_identity_sha256 VARCHAR,
    source_path VARCHAR NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL,
    UNIQUE (trade_date, revision)
);

CREATE TABLE IF NOT EXISTS publication_heads (
    trade_date DATE PRIMARY KEY,
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id)
);

CREATE TABLE IF NOT EXISTS publication_artifacts (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    artifact_name VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    file_sha256 VARCHAR NOT NULL,
    logical_digest_version VARCHAR NOT NULL,
    logical_sha256 VARCHAR NOT NULL,
    row_count BIGINT NOT NULL,
    columns_json JSON NOT NULL,
    primary_key_json JSON NOT NULL,
    PRIMARY KEY (publication_id, artifact_name)
);

CREATE TABLE IF NOT EXISTS market_daily (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    trade_date DATE NOT NULL,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, trade_date)
);

CREATE TABLE IF NOT EXISTS sector_daily (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    sector_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    sector_name VARCHAR,
    sector_type VARCHAR,
    primary_pattern VARCHAR,
    display_rank DOUBLE,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, sector_id)
);

CREATE TABLE IF NOT EXISTS stock_daily (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    security_name VARCHAR,
    primary_pattern VARCHAR,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, security_id)
);

CREATE TABLE IF NOT EXISTS candidate_daily (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    security_name VARCHAR,
    primary_pattern VARCHAR,
    research_priority VARCHAR,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, security_id)
);

CREATE TABLE IF NOT EXISTS structure_details (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    queue_name VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, queue_name, security_id)
);

CREATE TABLE IF NOT EXISTS queue_memberships (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    queue_name VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    queue_tier VARCHAR NOT NULL,
    source_v2_class VARCHAR,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, queue_name, security_id)
);

CREATE TABLE IF NOT EXISTS unified_board (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    payload_json JSON NOT NULL,
    PRIMARY KEY (publication_id, security_id)
);
CREATE TABLE IF NOT EXISTS queue_rankings (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id), security_id VARCHAR NOT NULL,
    payload_json JSON NOT NULL, PRIMARY KEY (publication_id, security_id)
);

CREATE TABLE IF NOT EXISTS membership_snapshots (
    membership_snapshot_id VARCHAR PRIMARY KEY,
    trade_date DATE NOT NULL,
    snapshot_version VARCHAR NOT NULL,
    logical_sha256 VARCHAR NOT NULL,
    row_count BIGINT NOT NULL,
    UNIQUE (trade_date, logical_sha256)
);

CREATE TABLE IF NOT EXISTS membership_entries (
    membership_snapshot_id VARCHAR NOT NULL REFERENCES membership_snapshots(membership_snapshot_id),
    sector_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    payload_json JSON NOT NULL,
    PRIMARY KEY (membership_snapshot_id, sector_id, security_id)
);

CREATE TABLE IF NOT EXISTS publication_memberships (
    publication_id VARCHAR PRIMARY KEY REFERENCES publications(publication_id),
    membership_snapshot_id VARCHAR NOT NULL REFERENCES membership_snapshots(membership_snapshot_id)
);

CREATE TABLE IF NOT EXISTS audit_receipts (
    receipt_id VARCHAR PRIMARY KEY,
    phase VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    payload_json JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (job_id VARCHAR PRIMARY KEY, job_key VARCHAR UNIQUE, status VARCHAR NOT NULL, payload_json JSON);
CREATE TABLE IF NOT EXISTS job_attempts (job_id VARCHAR NOT NULL, attempt INTEGER NOT NULL, status VARCHAR NOT NULL, payload_json JSON, PRIMARY KEY(job_id, attempt));
CREATE TABLE IF NOT EXISTS job_events (job_id VARCHAR NOT NULL, attempt INTEGER NOT NULL, sequence BIGINT NOT NULL, event_time_utc TIMESTAMP NOT NULL, payload_json JSON, PRIMARY KEY(job_id, attempt, sequence));
CREATE TABLE IF NOT EXISTS source_packages (source_package_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS source_files (source_package_id VARCHAR NOT NULL, relative_path VARCHAR NOT NULL, payload_json JSON NOT NULL, PRIMARY KEY(source_package_id, relative_path));
CREATE TABLE IF NOT EXISTS metadata_snapshots (metadata_snapshot_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS source_bundles (source_bundle_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS security_versions (security_id VARCHAR NOT NULL, observed_at_utc TIMESTAMP NOT NULL, payload_json JSON NOT NULL, PRIMARY KEY(security_id, observed_at_utc));
CREATE TABLE IF NOT EXISTS sector_versions (sector_id VARCHAR NOT NULL, observed_at_utc TIMESTAMP NOT NULL, payload_json JSON NOT NULL, PRIMARY KEY(sector_id, observed_at_utc));
CREATE TABLE IF NOT EXISTS observations (observation_id VARCHAR PRIMARY KEY, publication_id VARCHAR, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS outcomes (observation_id VARCHAR NOT NULL, horizon INTEGER NOT NULL, target_revision INTEGER NOT NULL, payload_json JSON NOT NULL, PRIMARY KEY(observation_id, horizon, target_revision));
CREATE TABLE IF NOT EXISTS state_transitions (transition_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS storage_objects (storage_object_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS leases (lease_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS cleanup_jobs (cleanup_job_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
CREATE TABLE IF NOT EXISTS backup_catalog (backup_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL);
