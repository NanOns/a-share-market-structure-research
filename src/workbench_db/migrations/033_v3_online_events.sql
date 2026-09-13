-- V3 P09-02-C: bounded close-event storage only.
-- Hot-rank payloads/rows/batches remain outside these tables.
CREATE TABLE IF NOT EXISTS online_event_bundles (
    bundle_id VARCHAR PRIMARY KEY,
    trade_date DATE NOT NULL,
    source_batch_bindings JSON NOT NULL,
    source_statuses JSON NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    coverage JSON NOT NULL,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (personal_research_only = TRUE)
);

CREATE TABLE IF NOT EXISTS online_event_header (
    batch_id VARCHAR PRIMARY KEY REFERENCES online_batches(batch_id),
    counts JSON NOT NULL,
    rates JSON NOT NULL,
    scope JSON NOT NULL,
    source_notice VARCHAR,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (personal_research_only = TRUE)
);

CREATE TABLE IF NOT EXISTS online_pool_entries (
    batch_id VARCHAR NOT NULL REFERENCES online_batches(batch_id),
    pool_type VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    security_id VARCHAR,
    event_state VARCHAR NOT NULL,
    consecutive_limit_days INTEGER,
    m_days INTEGER,
    n_boards INTEGER,
    first_limit_time TIMESTAMP,
    last_limit_time TIMESTAMP,
    last_break_time TIMESTAMP,
    price DECIMAL(18, 6),
    amount DECIMAL(28, 2),
    seal_amount DECIMAL(28, 2),
    ret1 DOUBLE,
    turnover DOUBLE,
    float_market_cap DECIMAL(28, 2),
    open_count INTEGER,
    source_reason VARCHAR,
    source_fields JSON NOT NULL,
    quality_codes JSON NOT NULL,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (batch_id, pool_type, source_code),
    CHECK (personal_research_only = TRUE)
);

CREATE INDEX IF NOT EXISTS online_event_bundles_trade_date_idx
    ON online_event_bundles (trade_date, observed_at);

CREATE INDEX IF NOT EXISTS online_pool_entries_batch_pool_idx
    ON online_pool_entries (batch_id, pool_type, source_code);
