-- Pure-Core engineering sidecar, independent from final state and production heads.
CREATE TABLE v4.stock_prewatch_publications (
    publication_id text PRIMARY KEY,
    trade_date date NOT NULL,
    model_contract_id text NOT NULL CHECK (model_contract_id='STOCK_PREWATCH_V1'),
    parameter_set_id text NOT NULL,
    source_publication_id text NOT NULL,
    source_core_logical_digest char(64) NOT NULL,
    publication_digest char(64) NOT NULL CHECK (publication_digest ~ '^[0-9a-f]{64}$'),
    row_count integer NOT NULL CHECK (row_count>0),
    acceptance_scope text NOT NULL CHECK (acceptance_scope='ENGINEERING_CANDIDATE'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE v4.stock_prewatch_results (
    publication_id text NOT NULL REFERENCES v4.stock_prewatch_publications(publication_id),
    security_id text NOT NULL,
    trade_date date NOT NULL,
    model_contract_id text NOT NULL,
    parameter_set_id text NOT NULL,
    raw_qualification text NOT NULL CHECK (raw_qualification IN ('TRUE','FALSE','UNKNOWN')),
    emergence_axis text NOT NULL CHECK (emergence_axis IN ('LOW','MEDIUM','HIGH','UNKNOWN')),
    structure_quality_axis text NOT NULL CHECK (structure_quality_axis IN ('LOW','MEDIUM','HIGH','UNKNOWN')),
    risk_axis text NOT NULL CHECK (risk_axis IN ('LOW','MEDIUM','HIGH','EXTREME','UNKNOWN')),
    priority_bucket text NOT NULL CHECK (priority_bucket IN ('A','B','C','D','UNKNOWN_BUCKET','NOT_ELIGIBLE')),
    quality text NOT NULL,
    reasons jsonb NOT NULL CHECK (jsonb_typeof(reasons)='array'),
    input_digest char(64) NOT NULL CHECK (input_digest ~ '^[0-9a-f]{64}$'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
    payload_digest char(64) NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (publication_id,security_id),
    CHECK ((raw_qualification='FALSE' AND priority_bucket='NOT_ELIGIBLE') OR
           (raw_qualification='UNKNOWN' AND priority_bucket='UNKNOWN_BUCKET') OR
           (raw_qualification='TRUE' AND priority_bucket<>'NOT_ELIGIBLE'))
);
CREATE FUNCTION v4.guard_stock_prewatch_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.stock_prewatch_publications%ROWTYPE;
BEGIN
    SELECT * INTO STRICT p FROM v4.stock_prewatch_publications WHERE publication_id=NEW.publication_id;
    IF NEW.trade_date IS DISTINCT FROM p.trade_date OR NEW.model_contract_id IS DISTINCT FROM p.model_contract_id OR
       NEW.parameter_set_id IS DISTINCT FROM p.parameter_set_id OR NEW.payload->>'source_publication_id' IS DISTINCT FROM p.source_publication_id OR
       NEW.payload->>'source_core_logical_digest' IS DISTINCT FROM p.source_core_logical_digest THEN
        RAISE EXCEPTION 'STOCK_PREWATCH_PUBLICATION_BINDING_MISMATCH';
    END IF;
    IF NEW.payload->>'raw_qualification' IS DISTINCT FROM NEW.raw_qualification OR
       NEW.payload->>'emergence_axis' IS DISTINCT FROM NEW.emergence_axis OR
       NEW.payload->>'structure_quality_axis' IS DISTINCT FROM NEW.structure_quality_axis OR
       NEW.payload->>'risk_axis' IS DISTINCT FROM NEW.risk_axis OR
       NEW.payload->>'priority_bucket' IS DISTINCT FROM NEW.priority_bucket OR
       NEW.payload->>'security_id' IS DISTINCT FROM NEW.security_id OR
       NEW.payload->>'publication_id' IS DISTINCT FROM NEW.publication_id OR
       NEW.payload->>'input_digest' IS DISTINCT FROM NEW.input_digest OR
       NEW.payload->>'trade_date' IS DISTINCT FROM NEW.trade_date::text OR
       NEW.payload->>'model_contract_id' IS DISTINCT FROM NEW.model_contract_id OR
       NEW.payload->>'parameter_set_id' IS DISTINCT FROM NEW.parameter_set_id OR
       NEW.payload->>'quality' IS DISTINCT FROM NEW.quality OR
       NEW.payload->'waiting_for' IS DISTINCT FROM NEW.reasons THEN
        RAISE EXCEPTION 'STOCK_PREWATCH_PAYLOAD_COLUMN_MISMATCH';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER v4_stock_prewatch_binding BEFORE INSERT ON v4.stock_prewatch_results
FOR EACH ROW EXECUTE FUNCTION v4.guard_stock_prewatch_binding();
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.stock_prewatch_publications
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.stock_prewatch_results
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
