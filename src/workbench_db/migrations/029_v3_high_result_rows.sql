-- V3 P03-02 high domain result rows.
-- The legacy table remains immutable as a compatibility source. Production
-- high reads resolve through high_result_daily, preferring the result-object
-- binding and falling back only for an unbound legacy slice.
CREATE TABLE IF NOT EXISTS high_result_rows (
    result_object_id VARCHAR NOT NULL REFERENCES analysis_result_objects(result_object_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    "window" INTEGER NOT NULL CHECK ("window" IN (20, 30, 60, 100)),
    contract_id VARCHAR NOT NULL,
    price_basis VARCHAR NOT NULL,
    prior_max_close DOUBLE,
    new_high BOOLEAN,
    at_prior_high BOOLEAN,
    streak INTEGER,
    is_left_censored BOOLEAN NOT NULL,
    dist_prior_high DOUBLE,
    valid_n INTEGER NOT NULL,
    quality_codes JSON NOT NULL,
    basis_json JSON NOT NULL,
    PRIMARY KEY (result_object_id, security_id, trade_date, "window")
);

CREATE INDEX IF NOT EXISTS high_result_rows_lookup_idx
    ON high_result_rows (result_object_id, trade_date, "window", security_id);

CREATE OR REPLACE VIEW high_result_daily AS
SELECT
    b.slice_id,
    b.result_object_id,
    h.* EXCLUDE (result_object_id)
FROM analysis_slice_result_bindings b
JOIN analysis_result_objects o
  ON o.result_object_id = b.result_object_id
 AND o.domain = 'high'
JOIN high_result_rows h
  ON h.result_object_id = b.result_object_id
UNION ALL
SELECT
    legacy.slice_id,
    CAST(NULL AS VARCHAR) AS result_object_id,
    legacy.* EXCLUDE (slice_id)
FROM stock_high_daily legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM analysis_slice_result_bindings bound
    WHERE bound.slice_id = legacy.slice_id
);
