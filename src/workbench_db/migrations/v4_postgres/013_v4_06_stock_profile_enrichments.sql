-- V4-06 Supplemental Enrichment. These rows are append-only sidecars to an
-- existing publication and cannot move or revise any Core publication head.
CREATE TABLE IF NOT EXISTS v4.supplemental_enrichment_manifests (
    publication_id text NOT NULL REFERENCES v4.publications(publication_id),
    enrichment_revision integer NOT NULL CHECK (enrichment_revision > 0),
    provider text NOT NULL CHECK (provider = 'BAOSTOCK'),
    source_contract_id text NOT NULL,
    field_map_version text NOT NULL,
    parameter_digest char(64) NOT NULL CHECK (parameter_digest ~ '^[0-9a-f]{64}$'),
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    provider_asof date,
    security_count integer NOT NULL CHECK (security_count >= 0),
    strict_bound_count integer NOT NULL CHECK (strict_bound_count >= 0),
    soft_bound_count integer NOT NULL CHECK (soft_bound_count >= 0),
    unavailable_count integer NOT NULL CHECK (unavailable_count >= 0),
    source_revision_set_digest char(64) NOT NULL CHECK (source_revision_set_digest ~ '^[0-9a-f]{64}$'),
    logical_digest char(64) NOT NULL CHECK (logical_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publication_id, enrichment_revision, provider),
    CHECK (strict_bound_count + soft_bound_count + unavailable_count <= security_count),
    CHECK (ingested_at >= observed_at)
);

CREATE TABLE IF NOT EXISTS v4.stock_profile_enrichments (
    publication_id text NOT NULL,
    security_id text NOT NULL,
    enrichment_revision integer NOT NULL CHECK (enrichment_revision > 0),
    provider text NOT NULL CHECK (provider = 'BAOSTOCK'),
    trade_date date NOT NULL,
    query_identity jsonb NOT NULL CHECK (
        jsonb_typeof(query_identity) = 'object'
        AND query_identity ?& ARRAY['provider_code','frequency','start_date','end_date','adjustflag']
    ),
    source_contract_id text NOT NULL,
    source_contract_version text NOT NULL,
    field_map_version text NOT NULL,
    raw_source_value text,
    raw_source_unit text,
    turnover_rate double precision CHECK (turnover_rate IS NULL OR (turnover_rate >= 0 AND turnover_rate <= 1)),
    turnover_ma5 double precision,
    turnover_median20 double precision,
    turnover_ratio20 double precision CHECK (turnover_ratio20 IS NULL OR turnover_ratio20 >= 0),
    turnover_pct5 double precision CHECK (turnover_pct5 IS NULL OR (turnover_pct5 >= 0 AND turnover_pct5 <= 1)),
    turnover_pct20 double precision CHECK (turnover_pct20 IS NULL OR (turnover_pct20 >= 0 AND turnover_pct20 <= 1)),
    turnover_pct60 double precision CHECK (turnover_pct60 IS NULL OR (turnover_pct60 >= 0 AND turnover_pct60 <= 1)),
    turnover_delta3 double precision,
    turnover_state text NOT NULL,
    turnover_context text NOT NULL,
    supplemental_participation_context jsonb NOT NULL,
    provider_asof date,
    binding_quality text NOT NULL CHECK (binding_quality IN (
        'BOUND_STRICT','BOUND_SOFT','UNAVAILABLE','STALE','MISSING','UNBOUND','SOURCE_NOT_READY'
    )),
    quality_codes jsonb NOT NULL,
    source_revision_id text NOT NULL,
    source_digest char(64) NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publication_id, enrichment_revision, security_id, provider),
    FOREIGN KEY (publication_id, enrichment_revision, provider)
        REFERENCES v4.supplemental_enrichment_manifests(publication_id, enrichment_revision, provider),
    CHECK (binding_quality = 'BOUND_STRICT' OR turnover_context IN ('UNKNOWN','DIAGNOSTIC_ONLY'))
);

CREATE INDEX IF NOT EXISTS ix_stock_profile_enrichments_publication_security
    ON v4.stock_profile_enrichments (publication_id, security_id, enrichment_revision DESC);

DROP TRIGGER IF EXISTS v4_append_only_guard ON v4.supplemental_enrichment_manifests;
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.supplemental_enrichment_manifests
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
DROP TRIGGER IF EXISTS v4_append_only_guard ON v4.stock_profile_enrichments;
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.stock_profile_enrichments
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
