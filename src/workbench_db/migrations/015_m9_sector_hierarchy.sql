-- M9 versioned local TDX hierarchy materialisation.
CREATE TABLE tdx_sector_hierarchy_versions (
    hierarchy_version VARCHAR PRIMARY KEY,
    contract_id VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    source_hashes JSON NOT NULL,
    source_digest VARCHAR NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE tdx_sector_hierarchy_nodes (
    hierarchy_version VARCHAR NOT NULL REFERENCES tdx_sector_hierarchy_versions(hierarchy_version),
    sector_type VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    sector_code VARCHAR NOT NULL,
    sector_name VARCHAR NOT NULL,
    parent_sector_id VARCHAR,
    parent_sector_name VARCHAR,
    hierarchy_level_code VARCHAR NOT NULL,
    relation_basis VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    source_hash VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    PRIMARY KEY (hierarchy_version, sector_type, sector_id)
);

CREATE INDEX tdx_sector_hierarchy_nodes_lookup_idx
    ON tdx_sector_hierarchy_nodes (hierarchy_version, sector_type, sector_code);

CREATE TABLE analysis_snapshot_hierarchy (
    snapshot_id VARCHAR PRIMARY KEY REFERENCES analysis_snapshots(snapshot_id),
    hierarchy_version VARCHAR NOT NULL REFERENCES tdx_sector_hierarchy_versions(hierarchy_version),
    source_hash VARCHAR NOT NULL,
    bound_at TIMESTAMP NOT NULL
);
