-- R1/R2 projections coexist as distinct versioned relations in fixed schema v4.
CREATE TABLE IF NOT EXISTS v4.read_versions_r1 (
    token text NOT NULL, day text NOT NULL, digest text NOT NULL,
    contract text NOT NULL, sealed boolean NOT NULL DEFAULT false,
    PRIMARY KEY(token,day)
);
CREATE TABLE IF NOT EXISTS v4.read_items_r1 (
    token text NOT NULL, day text NOT NULL, domain text NOT NULL,
    entity_id text NOT NULL, symbol text, display_name text,
    aliases text[] NOT NULL, search_parts text[] NOT NULL,
    sector_ids text[] NOT NULL, values_json jsonb NOT NULL,
    summary jsonb NOT NULL, detail jsonb NOT NULL, detail_sha256 text NOT NULL,
    PRIMARY KEY(token,day,domain,entity_id),
    FOREIGN KEY(token,day) REFERENCES v4.read_versions_r1(token,day)
);
CREATE TABLE IF NOT EXISTS v4.read_responses_r1 (
    token text NOT NULL, day text NOT NULL, path text NOT NULL,
    payload jsonb NOT NULL, payload_sha256 text NOT NULL,
    PRIMARY KEY(token,day,path),
    FOREIGN KEY(token,day) REFERENCES v4.read_versions_r1(token,day)
);
CREATE INDEX IF NOT EXISTS read_items_r1_order ON v4.read_items_r1(token,day,domain,entity_id);

CREATE TABLE IF NOT EXISTS v4.read_versions_r2 (
    context_id text NOT NULL, day text NOT NULL, digest text NOT NULL,
    contract text NOT NULL, sealed boolean NOT NULL DEFAULT false,
    PRIMARY KEY(context_id,day)
);
CREATE TABLE IF NOT EXISTS v4.read_items_r2 (
    context_id text NOT NULL, day text NOT NULL, domain text NOT NULL,
    entity_id text NOT NULL, symbol text, display_name text,
    aliases text[] NOT NULL, search_parts text[] NOT NULL,
    sector_ids text[] NOT NULL, values_json jsonb NOT NULL,
    summary jsonb NOT NULL, detail jsonb NOT NULL, detail_sha256 text NOT NULL,
    PRIMARY KEY(context_id,day,domain,entity_id),
    FOREIGN KEY(context_id,day) REFERENCES v4.read_versions_r2(context_id,day)
);
CREATE TABLE IF NOT EXISTS v4.read_responses_r2 (
    context_id text NOT NULL, day text NOT NULL, path text NOT NULL,
    payload jsonb NOT NULL, payload_sha256 text NOT NULL,
    PRIMARY KEY(context_id,day,path),
    FOREIGN KEY(context_id,day) REFERENCES v4.read_versions_r2(context_id,day)
);
CREATE INDEX IF NOT EXISTS read_items_r2_order ON v4.read_items_r2(context_id,day,domain,entity_id);

CREATE TABLE IF NOT EXISTS v4.read_index_migration_map_r1 (
    generation text NOT NULL CHECK(generation IN ('R1','R2')),
    source_schema text NOT NULL,
    context_id text NOT NULL,
    day text NOT NULL,
    digest text NOT NULL,
    contract text NOT NULL,
    domain_counts jsonb NOT NULL,
    response_count bigint NOT NULL,
    verification jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(generation,source_schema,context_id,day)
);
