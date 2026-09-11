CREATE TABLE IF NOT EXISTS relation_revisions (
    source_scope VARCHAR NOT NULL,
    revision_no INTEGER NOT NULL,
    revision_id VARCHAR UNIQUE NOT NULL,
    previous_revision_no INTEGER,
    edge_content_hash VARCHAR NOT NULL,
    parser_contract VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (source_scope, revision_no)
);

CREATE TABLE IF NOT EXISTS relation_edge_intervals (
    source_scope VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    from_revision INTEGER NOT NULL,
    to_revision INTEGER,
    source_kind VARCHAR NOT NULL,
    PRIMARY KEY (source_scope, sector_id, security_id, from_revision),
    CHECK (to_revision IS NULL OR to_revision > from_revision)
);

CREATE TABLE IF NOT EXISTS relation_observations (
    observation_id VARCHAR PRIMARY KEY,
    source_scope VARCHAR NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    source_effective_date DATE,
    source_file_hashes JSON NOT NULL,
    revision_no INTEGER NOT NULL,
    attribute_version_id VARCHAR,
    hierarchy_version VARCHAR,
    quality VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS relation_snapshot_bindings (
    legacy_membership_snapshot_id VARCHAR PRIMARY KEY REFERENCES membership_snapshots(membership_snapshot_id),
    observation_id VARCHAR NOT NULL REFERENCES relation_observations(observation_id),
    revision_no INTEGER NOT NULL,
    attribute_version_id VARCHAR,
    hierarchy_version VARCHAR,
    legacy_payload_basis JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS relation_publication_bindings (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    source_scope VARCHAR NOT NULL,
    observation_id VARCHAR NOT NULL REFERENCES relation_observations(observation_id),
    revision_no INTEGER NOT NULL,
    attribute_version_id VARCHAR,
    hierarchy_version VARCHAR,
    PRIMARY KEY (publication_id, source_scope)
);

CREATE TABLE IF NOT EXISTS sector_attribute_versions (
    source_scope VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    attribute_version_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    role VARCHAR,
    semantic_bucket VARCHAR,
    content_hash VARCHAR NOT NULL,
    PRIMARY KEY (source_scope, sector_id, attribute_version_id)
);

CREATE TABLE IF NOT EXISTS sector_attribute_revisions (
    source_scope VARCHAR NOT NULL,
    attribute_revision INTEGER NOT NULL,
    attribute_set_hash VARCHAR NOT NULL,
    PRIMARY KEY (source_scope, attribute_revision),
    UNIQUE (source_scope, attribute_set_hash)
);

CREATE TABLE IF NOT EXISTS sector_attribute_revision_bindings (
    source_scope VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    from_attribute_revision INTEGER NOT NULL,
    to_attribute_revision INTEGER,
    attribute_version_id VARCHAR NOT NULL,
    PRIMARY KEY (source_scope, sector_id, from_attribute_revision),
    CHECK (to_attribute_revision IS NULL OR to_attribute_revision > from_attribute_revision)
);

CREATE INDEX IF NOT EXISTS idx_relation_edge_intervals_sector
    ON relation_edge_intervals(source_scope, sector_id, from_revision, to_revision);
CREATE INDEX IF NOT EXISTS idx_relation_edge_intervals_security
    ON relation_edge_intervals(source_scope, security_id, from_revision, to_revision);
CREATE INDEX IF NOT EXISTS idx_relation_observations_scope_date
    ON relation_observations(source_scope, observed_at);
