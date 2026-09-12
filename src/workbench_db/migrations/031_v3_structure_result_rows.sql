-- V3 P03-03 structure domain result rows.
-- The legacy table remains immutable as a compatibility source. Production
-- structure reads resolve through historical_structure_result_daily, preferring
-- the result-object binding and falling back only for an unbound legacy slice.
CREATE TABLE IF NOT EXISTS structure_result_rows (
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    queue_name VARCHAR NOT NULL,
    hit BOOLEAN,
    tier VARCHAR,
    source_class VARCHAR NOT NULL,
    research_band VARCHAR,
    queue_rank BIGINT,
    tier_rank BIGINT,
    transition VARCHAR,
    structure_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    evidence JSON NOT NULL,
    quality_codes JSON NOT NULL,
    PRIMARY KEY (result_object_id, security_id, trade_date, queue_name)
);

CREATE INDEX IF NOT EXISTS structure_result_rows_lookup_idx
    ON structure_result_rows (result_object_id, trade_date, queue_name, security_id);

CREATE OR REPLACE VIEW historical_structure_result_daily AS
SELECT
    b.slice_id,
    b.result_object_id,
    r.* EXCLUDE (result_object_id)
FROM analysis_slice_result_bindings b
JOIN analysis_result_objects o
  ON o.result_object_id = b.result_object_id
 AND o.domain = 'structure'
JOIN structure_result_rows r
  ON r.result_object_id = b.result_object_id
UNION ALL
SELECT
    legacy.slice_id,
    CAST(NULL AS VARCHAR) AS result_object_id,
    legacy.* EXCLUDE (slice_id)
FROM historical_structure_daily legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM analysis_slice_result_bindings bound
    WHERE bound.slice_id = legacy.slice_id
);
