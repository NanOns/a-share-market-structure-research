-- V3 P03-03 summary-domain result rows.
-- The legacy summary table remains immutable as a compatibility/audit source.
CREATE TABLE IF NOT EXISTS structure_summary_result_rows (
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    queues_json JSON NOT NULL,
    research_band VARCHAR NOT NULL,
    research_band_quality VARCHAR NOT NULL,
    unique_hit_count BIGINT NOT NULL,
    queue_contract VARCHAR NOT NULL,
    PRIMARY KEY (result_object_id, security_id, trade_date)
);

CREATE INDEX IF NOT EXISTS structure_summary_result_rows_lookup_idx
    ON structure_summary_result_rows (result_object_id, trade_date, security_id);

CREATE OR REPLACE VIEW structure_summary_result_daily AS
SELECT
    b.slice_id,
    b.result_object_id,
    r.* EXCLUDE (result_object_id)
FROM analysis_slice_result_bindings b
JOIN analysis_result_objects o
  ON o.result_object_id = b.result_object_id
 AND o.domain = 'summary'
JOIN structure_summary_result_rows r
  ON r.result_object_id = b.result_object_id
UNION ALL
SELECT
    legacy.slice_id,
    CAST(NULL AS VARCHAR) AS result_object_id,
    legacy.* EXCLUDE (slice_id)
FROM stock_structure_summary_daily legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM analysis_slice_result_bindings bound
    WHERE bound.slice_id = legacy.slice_id
);
