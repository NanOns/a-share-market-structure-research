-- V3 P03-01 content-addressed result objects and slice bindings.
CREATE TABLE IF NOT EXISTS analysis_result_objects (
    result_object_id VARCHAR PRIMARY KEY,
    domain VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    semantic_contract VARCHAR NOT NULL,
    value_hash VARCHAR NOT NULL UNIQUE,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    storage_kind VARCHAR NOT NULL CHECK (storage_kind IN ('PARQUET', 'DUCKDB')),
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_slice_result_bindings (
    slice_id VARCHAR PRIMARY KEY REFERENCES analysis_slices(slice_id),
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
    identity_evidence JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS analysis_slice_result_bindings_object_idx
    ON analysis_slice_result_bindings (result_object_id);
