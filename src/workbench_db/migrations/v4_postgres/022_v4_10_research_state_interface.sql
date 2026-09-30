-- V4-10 engineering sidecar; no production state heads or prior schemas are moved.
CREATE TABLE v4.research_state_engineering_publications (
    publication_id text PRIMARY KEY,
    revision_of text REFERENCES v4.research_state_engineering_publications(publication_id),
    model_contract_id text NOT NULL CHECK (model_contract_id='RESEARCH_STATE_V1'),
    consumer_contract_id text NOT NULL CHECK (consumer_contract_id='V4_10_REDUCER_INTERFACE_V1'),
    parameter_set_id text NOT NULL CHECK (parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1'),
    publication_digest char(64) NOT NULL CHECK (publication_digest ~ '^[0-9a-f]{64}$'),
    row_count integer NOT NULL CHECK (row_count>0),
    acceptance_scope text NOT NULL CHECK (acceptance_scope='ENGINEERING_INTERFACE_ONLY'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (revision_of IS DISTINCT FROM publication_id)
);
CREATE TABLE v4.research_state_engineering_results (
    publication_id text NOT NULL REFERENCES v4.research_state_engineering_publications(publication_id),
    state_publication_id text NOT NULL,
    entity_id text NOT NULL,
    entity_type text NOT NULL CHECK (entity_type IN ('STOCK','SECTOR')),
    episode_key text NOT NULL,
    episode_id text,
    parent_episode_id text,
    trade_date date NOT NULL,
    session_index integer NOT NULL CHECK (session_index>=0),
    model_contract_id text NOT NULL,
    parameter_set_id text NOT NULL,
    maturity text NOT NULL CHECK (maturity IN ('NONE','SEED','PREWATCH','WARM','CONFIRMED')),
    health text NOT NULL CHECK (health IN ('IMPROVING','STABLE','WEAKENING','DAMAGED','EXHAUSTED','UNKNOWN')),
    validity text NOT NULL CHECK (validity IN ('VALID','INVALIDATED','UNKNOWN')),
    tracking text NOT NULL CHECK (tracking IN ('ACTIVE','FOLLOWUP','CLOSED')),
    scenario text NOT NULL,
    state_freshness text NOT NULL CHECK (state_freshness IN ('FRESH','STALE')),
    final_eligibility text NOT NULL CHECK (final_eligibility IN ('TRUE','FALSE','UNKNOWN')),
    prior_state_binding jsonb NOT NULL,
    input_publication_ids jsonb NOT NULL CHECK (jsonb_typeof(input_publication_ids)='array' AND jsonb_array_length(input_publication_ids)>0),
    matched_predicates jsonb NOT NULL CHECK (jsonb_typeof(matched_predicates)='array'),
    unknown_predicates jsonb NOT NULL CHECK (jsonb_typeof(unknown_predicates)='array'),
    transition_reasons jsonb NOT NULL CHECK (jsonb_typeof(transition_reasons)='array'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
    payload_digest char(64) NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (publication_id,entity_id,entity_type,episode_key),
    UNIQUE (publication_id,state_publication_id),
    CHECK (episode_key=coalesce(episode_id,'NO_EPISODE')),
    CHECK (state_freshness<>'STALE' OR final_eligibility='UNKNOWN'),
    CHECK (entity_type<>'STOCK' OR maturity<>'WARM'),
    CHECK ((entity_type='STOCK' AND scenario IN ('SETUP','LAUNCH_CONFIRM','RECOVERY_TURN','STRONG_PULLBACK','TREND_CONTINUE','NONE')) OR
           (entity_type='SECTOR' AND scenario IN ('BASE_BUILD','BREADTH_BUILD','RECOVERY_BUILD','BROADENING','REACCELERATING','SUSTAINED','NONE')))
);
CREATE FUNCTION v4.guard_research_state_engineering_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.research_state_engineering_publications%ROWTYPE;
BEGIN
    SELECT * INTO STRICT p FROM v4.research_state_engineering_publications WHERE publication_id=NEW.publication_id;
    IF NEW.model_contract_id IS DISTINCT FROM p.model_contract_id OR NEW.parameter_set_id IS DISTINCT FROM p.parameter_set_id THEN
        RAISE EXCEPTION 'RESEARCH_STATE_PUBLICATION_BINDING_MISMATCH';
    END IF;
    IF NEW.payload->>'publication_id' IS DISTINCT FROM NEW.state_publication_id OR
       NEW.payload->>'entity_id' IS DISTINCT FROM NEW.entity_id OR NEW.payload->>'entity_type' IS DISTINCT FROM NEW.entity_type OR
       NEW.payload->>'episode_id' IS DISTINCT FROM NEW.episode_id OR NEW.payload->>'parent_episode_id' IS DISTINCT FROM NEW.parent_episode_id OR
       NEW.payload->>'trade_date' IS DISTINCT FROM NEW.trade_date::text OR NEW.payload->>'session_index' IS DISTINCT FROM NEW.session_index::text OR
       NEW.payload->>'model_contract_id' IS DISTINCT FROM NEW.model_contract_id OR NEW.payload->>'parameter_set_id' IS DISTINCT FROM NEW.parameter_set_id OR
       NEW.payload->>'maturity' IS DISTINCT FROM NEW.maturity OR NEW.payload->>'health' IS DISTINCT FROM NEW.health OR
       NEW.payload->>'validity' IS DISTINCT FROM NEW.validity OR NEW.payload->>'tracking' IS DISTINCT FROM NEW.tracking OR
       NEW.payload->>'scenario' IS DISTINCT FROM NEW.scenario OR NEW.payload->>'state_freshness' IS DISTINCT FROM NEW.state_freshness OR
       NEW.payload->>'final_eligibility' IS DISTINCT FROM NEW.final_eligibility OR
       NEW.payload->'prior_state_binding' IS DISTINCT FROM NEW.prior_state_binding OR
       NEW.payload->'input_publication_ids' IS DISTINCT FROM NEW.input_publication_ids OR
       NEW.payload->'matched_predicates' IS DISTINCT FROM NEW.matched_predicates OR
       NEW.payload->'unknown_predicates' IS DISTINCT FROM NEW.unknown_predicates OR
       NEW.payload->'transition_reasons' IS DISTINCT FROM NEW.transition_reasons THEN
        RAISE EXCEPTION 'RESEARCH_STATE_PAYLOAD_COLUMN_MISMATCH';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER v4_research_state_binding BEFORE INSERT ON v4.research_state_engineering_results
FOR EACH ROW EXECUTE FUNCTION v4.guard_research_state_engineering_binding();
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.research_state_engineering_publications
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.research_state_engineering_results
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
