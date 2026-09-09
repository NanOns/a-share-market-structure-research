-- M8B-02 / 010_historical_structure
-- Reconstructed structure rows are immutable and separate from observations.
CREATE TABLE historical_structure_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    queue_name VARCHAR NOT NULL,
    hit BOOLEAN,
    tier VARCHAR,
    source_class VARCHAR NOT NULL,
    research_band VARCHAR NOT NULL,
    queue_rank BIGINT,
    tier_rank BIGINT,
    transition VARCHAR,
    structure_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    evidence JSON NOT NULL,
    quality_codes JSON NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date, queue_name)
);

CREATE TABLE stock_structure_summary_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    queues_json JSON NOT NULL,
    research_band VARCHAR NOT NULL,
    research_band_quality VARCHAR NOT NULL,
    unique_hit_count BIGINT NOT NULL,
    queue_contract VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, security_id, trade_date)
);

CREATE INDEX historical_structure_daily_date_idx
    ON historical_structure_daily (slice_id, trade_date, queue_name, security_id);
