-- Engineering candidate sidecar. No production permission or final accepted head.
CREATE TABLE v4.sector_algorithm_publications_r5 (
    publication_id text PRIMARY KEY,
    target_trade_date date NOT NULL,
    membership_snapshot_id text NOT NULL,
    parameter_set_id text NOT NULL,
    input_digests jsonb NOT NULL CHECK (jsonb_typeof(input_digests)='object'),
    publication_digest char(64) NOT NULL CHECK (publication_digest ~ '^[0-9a-f]{64}$'),
    acceptance_scope text NOT NULL CHECK (acceptance_scope='ENGINEERING_CANDIDATE'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE v4.sector_algorithm_results_r5 (
    publication_id text NOT NULL REFERENCES v4.sector_algorithm_publications_r5(publication_id),
    sector_id text NOT NULL,
    sector_type text NOT NULL CHECK (sector_type IN ('INDUSTRY','THEME')),
    model_contract_id text NOT NULL,
    parameter_set_id text NOT NULL,
    membership_snapshot_id text NOT NULL,
    target_trade_date date NOT NULL,
    max_source_date date NOT NULL CHECK (max_source_date<=target_trade_date),
    input_digests jsonb NOT NULL CHECK (jsonb_typeof(input_digests)='object'),
    output_state text NOT NULL,
    predicates jsonb NOT NULL CHECK (jsonb_typeof(predicates)='object'),
    quality text NOT NULL,
    reason_codes jsonb NOT NULL CHECK (jsonb_typeof(reason_codes)='array'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
    payload_digest char(64) NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publication_id,sector_id,model_contract_id)
);
CREATE FUNCTION v4.guard_sector_algorithm_r5_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.sector_algorithm_publications_r5%ROWTYPE;
BEGIN
    SELECT * INTO STRICT p FROM v4.sector_algorithm_publications_r5 WHERE publication_id=NEW.publication_id;
    IF NEW.target_trade_date<>p.target_trade_date OR NEW.membership_snapshot_id<>p.membership_snapshot_id
       OR NEW.parameter_set_id<>p.parameter_set_id OR NEW.input_digests<>p.input_digests THEN
       RAISE EXCEPTION 'R5_PUBLICATION_BINDING_MISMATCH';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER v4_sector_algorithm_binding BEFORE INSERT ON v4.sector_algorithm_results_r5
FOR EACH ROW EXECUTE FUNCTION v4.guard_sector_algorithm_r5_binding();
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.sector_algorithm_publications_r5
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.sector_algorithm_results_r5
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
