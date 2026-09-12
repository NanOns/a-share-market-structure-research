-- V3 P03-03 member_state domain result rows.
-- The legacy table remains immutable as a compatibility source. Production
-- member-state reads resolve through member_state_result_daily, preferring the
-- result-object binding and falling back only for an unbound legacy slice.
CREATE TABLE IF NOT EXISTS member_state_result_rows (
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
    sector_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    member_present BOOLEAN NOT NULL,
    member_rank DOUBLE,
    rank_valid_count BIGINT NOT NULL,
    member_percentile DOUBLE,
    strong_state BOOLEAN,
    strong_predicates JSON NOT NULL,
    structure_hit BOOLEAN,
    high_hit BOOLEAN,
    member_change_kind VARCHAR,
    strength_change_kind VARCHAR,
    previous_rank DOUBLE,
    rank_delta DOUBLE,
    queue_refs JSON NOT NULL,
    high_refs JSON NOT NULL,
    history_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    PRIMARY KEY (result_object_id, sector_id, security_id, trade_date)
);

CREATE INDEX IF NOT EXISTS member_state_result_rows_lookup_idx
    ON member_state_result_rows (result_object_id, trade_date, sector_id, security_id);

CREATE OR REPLACE VIEW member_state_result_daily AS
SELECT
    b.slice_id,
    b.result_object_id,
    m.* EXCLUDE (result_object_id)
FROM analysis_slice_result_bindings b
JOIN analysis_result_objects o
  ON o.result_object_id = b.result_object_id
 AND o.domain = 'member_state'
JOIN member_state_result_rows m
  ON m.result_object_id = b.result_object_id
UNION ALL
SELECT
    legacy.slice_id,
    CAST(NULL AS VARCHAR) AS result_object_id,
    legacy.* EXCLUDE (slice_id)
FROM sector_member_state_daily legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM analysis_slice_result_bindings bound
    WHERE bound.slice_id = legacy.slice_id
);
