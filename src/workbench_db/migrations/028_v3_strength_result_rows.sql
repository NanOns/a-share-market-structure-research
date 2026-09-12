-- V3 P03-02 strength domain result rows.
-- The legacy table remains immutable as a compatibility source.  Production
-- strength reads resolve through strength_result_daily, preferring the
-- result-object binding and falling back only for an unbound legacy slice.
CREATE TABLE IF NOT EXISTS strength_result_rows (
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    contract_id VARCHAR NOT NULL,
    price_basis VARCHAR NOT NULL,
    ret5 DOUBLE,
    ret10 DOUBLE,
    ret20 DOUBLE,
    ret60 DOUBLE,
    rs5 DOUBLE,
    rs10 DOUBLE,
    rs20 DOUBLE,
    rs60 DOUBLE,
    rps5 DOUBLE,
    rps10 DOUBLE,
    rps20 DOUBLE,
    rps60 DOUBLE,
    rps_valid_universe_count5 INTEGER NOT NULL,
    rps_valid_universe_count10 INTEGER NOT NULL,
    rps_valid_universe_count20 INTEGER NOT NULL,
    rps_valid_universe_count60 INTEGER NOT NULL,
    quality_codes JSON NOT NULL,
    basis_json JSON NOT NULL,
    PRIMARY KEY (result_object_id, security_id, trade_date)
);

CREATE INDEX IF NOT EXISTS strength_result_rows_lookup_idx
    ON strength_result_rows (result_object_id, trade_date, security_id);

CREATE OR REPLACE VIEW strength_result_daily AS
SELECT
    b.slice_id,
    b.result_object_id,
    s.* EXCLUDE (result_object_id)
FROM analysis_slice_result_bindings b
JOIN analysis_result_objects o
  ON o.result_object_id = b.result_object_id
 AND o.domain = 'strength'
JOIN strength_result_rows s
  ON s.result_object_id = b.result_object_id
UNION ALL
SELECT
    legacy.slice_id,
    CAST(NULL AS VARCHAR) AS result_object_id,
    legacy.* EXCLUDE (slice_id)
FROM stock_strength_daily legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM analysis_slice_result_bindings bound
    WHERE bound.slice_id = legacy.slice_id
);
