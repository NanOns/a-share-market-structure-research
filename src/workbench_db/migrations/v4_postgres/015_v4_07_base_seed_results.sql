-- V4-07 BASE_SEED_V1 candidate results. This append-only sidecar is
-- publication-bound and never mutates accepted V4-05 Core publication rows.
CREATE TABLE v4.base_seed_results (
    publication_id text NOT NULL REFERENCES v4.publications(publication_id),
    trade_date date NOT NULL,
    security_id text NOT NULL,
    model_contract_id text NOT NULL CHECK (model_contract_id = 'BASE_SEED_V1'),
    parameter_set_id text NOT NULL CHECK (parameter_set_id = 'V4_07_BASE_SEED_PARAMETER_SET_V1'),
    source_publication_id text NOT NULL,
    source_core_logical_digest char(64) NOT NULL CHECK (source_core_logical_digest ~ '^[0-9a-f]{64}$'),
    input_digest char(64) NOT NULL CHECK (input_digest ~ '^[0-9a-f]{64}$'),
    fact_digest char(64) NOT NULL CHECK (fact_digest ~ '^[0-9a-f]{64}$'),
    base_seed_state text NOT NULL CHECK (base_seed_state IN ('TRUE', 'FALSE', 'UNKNOWN')),
    matched_seed_paths jsonb NOT NULL CHECK (
        jsonb_typeof(matched_seed_paths) = 'array'
        AND matched_seed_paths <@ '["S1", "S2"]'::jsonb
    ),
    domain_states jsonb NOT NULL CHECK (jsonb_typeof(domain_states) = 'object'),
    waiting_for jsonb NOT NULL CHECK (jsonb_typeof(waiting_for) = 'array'),
    invalid_if jsonb NOT NULL CHECK (jsonb_typeof(invalid_if) = 'array'),
    quality text NOT NULL CHECK (quality IN ('COMPLETE', 'PARTIAL_UNKNOWN')),
    quality_codes jsonb NOT NULL CHECK (jsonb_typeof(quality_codes) = 'array'),
    seed_participation_annotation text NOT NULL CHECK (
        seed_participation_annotation IN ('SUPPORTED', 'CONFLICTING', 'NEUTRAL', 'UNKNOWN')
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (
        publication_id, trade_date, security_id, model_contract_id, parameter_set_id, input_digest
    )
);

CREATE INDEX ix_v4_base_seed_results_publication_date_state
    ON v4.base_seed_results (publication_id, trade_date, base_seed_state);

CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.base_seed_results
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();