CREATE TABLE IF NOT EXISTS data_sources (
    source_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    source_class VARCHAR NOT NULL,
    adapter_version VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL,
    terms_state VARCHAR NOT NULL,
    capabilities JSON NOT NULL,
    cache_policy JSON NOT NULL,
    documentation_ref VARCHAR,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS online_fetch_runs (
    fetch_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    requested_at TIMESTAMP NOT NULL,
    received_at TIMESTAMP,
    status VARCHAR NOT NULL,
    error_code VARCHAR,
    http_status INTEGER,
    raw_hash VARCHAR,
    adapter_version VARCHAR NOT NULL,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS online_payloads (
    raw_hash VARCHAR PRIMARY KEY,
    storage_object_id VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    byte_count BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS online_batches (
    batch_id VARCHAR PRIMARY KEY,
    fetch_id VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    trade_date DATE,
    source_as_of TIMESTAMP,
    observed_at TIMESTAMP NOT NULL,
    first_seen_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    row_count INTEGER NOT NULL,
    logical_hash VARCHAR NOT NULL,
    adapter_version VARCHAR NOT NULL,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS online_rank_entries (
    batch_id VARCHAR NOT NULL,
    list_type VARCHAR NOT NULL,
    security_id VARCHAR,
    source_code VARCHAR NOT NULL,
    platform_rank INTEGER NOT NULL,
    previous_rank INTEGER,
    comparison_batch_id VARCHAR,
    rank_change_basis VARCHAR,
    extra JSON NOT NULL,
    PRIMARY KEY (batch_id, list_type, source_code)
);

CREATE TABLE IF NOT EXISTS online_security_map (
    source_id VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    valid_from DATE,
    valid_to DATE,
    security_id VARCHAR,
    exchange VARCHAR,
    mapping_version VARCHAR NOT NULL,
    evidence_ref VARCHAR NOT NULL,
    PRIMARY KEY (source_id, source_code, valid_from)
);

CREATE TABLE IF NOT EXISTS online_evidence (
    evidence_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL,
    evidence_type VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    source_code VARCHAR,
    trade_date DATE,
    event_time TIMESTAMP,
    published_at TIMESTAMP,
    first_seen_at TIMESTAMP NOT NULL,
    title VARCHAR,
    summary VARCHAR,
    text_hash VARCHAR NOT NULL,
    raw_ref VARCHAR NOT NULL,
    source_url VARCHAR,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS online_quote_entries (
    batch_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    quote_time TIMESTAMP NOT NULL,
    price DECIMAL(18, 6),
    ret1 DOUBLE,
    amount DECIMAL(28, 2),
    volume BIGINT,
    quote_state VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    price_unit VARCHAR NOT NULL,
    amount_unit VARCHAR NOT NULL,
    volume_unit VARCHAR NOT NULL,
    extra JSON NOT NULL,
    personal_research_only BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (batch_id, security_id)
);
