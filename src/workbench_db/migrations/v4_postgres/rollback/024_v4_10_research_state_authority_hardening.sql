DROP TRIGGER v4_state_authority_r1_2 ON v4.research_state_engineering_publications;
DROP TRIGGER v4_state_authority_r1_2 ON v4.research_state_engineering_results;
DROP FUNCTION v4.guard_controlled_state_publisher_r1_2();
DROP TABLE v4.research_state_boundary_prior_publications;
DROP TABLE v4.research_state_field_policy_r1_2;
ALTER TABLE v4.research_state_engineering_publications DROP COLUMN producer_attestation;
CREATE OR REPLACE FUNCTION v4.guard_state_identity_r1_1() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE f jsonb; field_name text; policy v4.research_state_field_policy_r1_1%ROWTYPE;
    source_manifest jsonb; cal jsonb; binding jsonb; prior_row jsonb; boundary jsonb; expected_index integer;
BEGIN
    IF NEW.payload->>'interface_contract_id' IS DISTINCT FROM 'V4_10_STATE_REDUCER_INTERFACE_R1_1' OR
       NEW.payload->>'canonicalization_contract_id' IS DISTINCT FROM 'V4_10_CANONICAL_JSON_R1_1' THEN
        RAISE EXCEPTION 'STATE_R1_1_INTERFACE_REQUIRED_FOR_NEW_WRITES';
    END IF;
    IF NEW.payload_digest IS DISTINCT FROM v4.state_digest_r1_1(NEW.payload) THEN RAISE EXCEPTION 'STATE_PAYLOAD_DIGEST_MISMATCH'; END IF;
    IF NEW.state_publication_id IS DISTINCT FROM 'V4_10:'||v4.state_digest_r1_1(NEW.payload-'publication_id') THEN
        RAISE EXCEPTION 'STATE_CONTENT_ADDRESS_IDENTITY_MISMATCH';
    END IF;
    IF NOT NEW.payload ?& ARRAY['publication_id','entity_id','entity_type','trade_date','session_index','calendar_publication_id','calendar_binding','mode',
        'maturity','health','validity','tracking','scenario','scenario_status','state_freshness','final_eligibility','raw_qualification','detector_statuses',
        'episode_id','parent_episode_id','invalidation_contract_id','prior_state_binding','input_publication_ids','model_contract_id','parameter_set_id','input_digest',
        'matched_predicates','unknown_predicates','transition_reasons','expiry_count','improvement_baseline','market_age','downgrade_candidate','downgrade_count',
        'exit_session_index','boundary_event','preserved_followup_episode_ids','interface_contract_id','canonicalization_contract_id','input_provenance','input_publication_manifest_digest','cutoff'] THEN
        RAISE EXCEPTION 'STATE_FULL_OUTPUT_SCHEMA_REQUIRED';
    END IF;
    IF NEW.interface_contract_id IS DISTINCT FROM NEW.payload->>'interface_contract_id' OR
       NEW.canonicalization_contract_id IS DISTINCT FROM NEW.payload->>'canonicalization_contract_id' OR
       NEW.calendar_publication_id IS DISTINCT FROM NEW.payload->>'calendar_publication_id' OR
       NEW.calendar_lineage_id IS DISTINCT FROM NEW.payload#>>'{calendar_binding,lineage_id}' OR
       NEW.calendar_manifest_digest IS DISTINCT FROM NEW.payload#>>'{calendar_binding,manifest_digest}' OR
       NEW.input_publication_manifest_digest IS DISTINCT FROM NEW.payload->>'input_publication_manifest_digest' OR
       NEW.input_provenance IS DISTINCT FROM NEW.payload->'input_provenance' OR
       NEW.boundary_event IS DISTINCT FROM NEW.payload->'boundary_event' OR
       NEW.prior_engineering_publication_id IS DISTINCT FROM NEW.payload#>>'{prior_state_binding,engineering_publication_id}' OR
       NEW.prior_row_payload_digest IS DISTINCT FROM NEW.payload#>>'{prior_state_binding,payload_digest}' THEN
        RAISE EXCEPTION 'STATE_LINEAGE_COLUMN_PAYLOAD_MISMATCH';
    END IF;
    IF jsonb_typeof(NEW.payload->'input_publication_ids') IS DISTINCT FROM 'array' OR
       jsonb_array_length(NEW.payload->'input_publication_ids')<1 OR
       EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.payload->'input_publication_ids') id WHERE jsonb_typeof(id)<>'string' OR length(id#>>'{}')>512 OR id#>>'{}' !~ '^[A-Za-z0-9][A-Za-z0-9_.:/-]*$') OR
       (SELECT count(*)<>count(DISTINCT id) FROM jsonb_array_elements(NEW.payload->'input_publication_ids') id) THEN
        RAISE EXCEPTION 'STATE_INPUT_PUBLICATION_MANIFEST_SHAPE_INVALID';
    END IF;
    IF NEW.input_publication_manifest_digest IS DISTINCT FROM v4.state_digest_r1_1(jsonb_build_object('input_publication_ids',NEW.payload->'input_publication_ids','fields',NEW.input_provenance)) THEN
        RAISE EXCEPTION 'STATE_INPUT_MANIFEST_DIGEST_MISMATCH';
    END IF;
    IF jsonb_typeof(NEW.input_provenance) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(NEW.input_provenance))<>13 THEN
        RAISE EXCEPTION 'STATE_FIELD_MANIFEST_INCOMPLETE';
    END IF;
    IF NEW.payload->>'mode'='ACCEPTED_FACT_INTERFACE' THEN
        IF EXISTS (SELECT 1 FROM jsonb_array_elements_text(NEW.input_publication_ids) id
                   WHERE NOT EXISTS (SELECT 1 FROM v4.research_state_input_manifests m WHERE m.publication_id=id AND m.manifest_kind='FACT_PUBLICATION')) THEN
            RAISE EXCEPTION 'STATE_INPUT_PUBLICATION_NOT_IN_TRUSTED_LEDGER';
        END IF;
        IF jsonb_typeof(NEW.payload->'cutoff') IS DISTINCT FROM 'string' OR
           NEW.payload->>'cutoff' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' OR
           left(NEW.payload->>'cutoff',10) IS DISTINCT FROM NEW.trade_date::text THEN
            RAISE EXCEPTION 'STATE_CUTOFF_REQUIRED';
        END IF;
        SELECT manifest INTO cal FROM v4.research_state_input_manifests WHERE publication_id=NEW.calendar_publication_id AND manifest_kind='MARKET_CALENDAR';
    END IF;
    FOR policy IN SELECT * FROM v4.research_state_field_policy_r1_1 LOOP
        field_name=policy.field; f=NEW.input_provenance->field_name;
        IF f IS NULL OR NOT f ?& ARRAY['field','value','quality','status','producer_contract_id','producer_parameter_set_id','publication_id','source_output_digest','source_field_payload','time_role','required','system_available_at'] OR
           f->>'field' IS DISTINCT FROM field_name OR f->>'time_role' IS DISTINCT FROM policy.time_role OR f->'required' IS DISTINCT FROM to_jsonb(policy.required) THEN
            RAISE EXCEPTION 'STATE_FIELD_POLICY_MISMATCH';
        END IF;
        IF f->>'status' IN ('NOT_IMPLEMENTED','NOT_APPLICABLE') THEN
            IF f->>'value' IS DISTINCT FROM 'UNKNOWN' OR f->>'quality' IS DISTINCT FROM 'UNKNOWN' OR
               f->'publication_id' IS DISTINCT FROM 'null'::jsonb OR f->'source_output_digest' IS DISTINCT FROM 'null'::jsonb OR
               f->>'producer_contract_id' IS DISTINCT FROM policy.producer_contract_id OR f->>'producer_parameter_set_id' IS DISTINCT FROM policy.producer_parameter_set_id THEN
                RAISE EXCEPTION 'STATE_NOT_IMPLEMENTED_FACT_MUST_BE_UNKNOWN';
            END IF;
        ELSIF f->>'status' IN ('IMPLEMENTED','SYNTHETIC') THEN
            IF f->>'source_output_digest' IS DISTINCT FROM v4.state_digest_r1_1(f->'source_field_payload') OR
               f#>>'{source_field_payload,field}' IS DISTINCT FROM field_name OR f#>'{source_field_payload,value}' IS DISTINCT FROM f->'value' OR
               NOT (NEW.payload->'input_publication_ids' ? (f->>'publication_id')) THEN
                RAISE EXCEPTION 'STATE_FIELD_SOURCE_IDENTITY_MISMATCH';
            END IF;
            IF f->>'status'='SYNTHETIC' THEN
                IF NEW.payload->>'mode'<>'SYNTHETIC_CONTRACT_VECTOR' OR f->>'publication_id' NOT LIKE 'SYNTHETIC_FACTS:%' OR f->>'producer_contract_id' NOT LIKE 'SYNTHETIC_%' THEN
                    RAISE EXCEPTION 'STATE_SYNTHETIC_NAMESPACE_MISMATCH';
                END IF;
            ELSE
                IF NOT policy.implemented OR NOT NEW.entity_type=ANY(policy.accepted_entity_types) OR f->>'producer_contract_id' IS DISTINCT FROM policy.producer_contract_id OR
                   f->>'producer_parameter_set_id' IS DISTINCT FROM policy.producer_parameter_set_id THEN RAISE EXCEPTION 'STATE_FIELD_PRODUCER_LINEAGE_MISMATCH'; END IF;
                SELECT manifest INTO source_manifest FROM v4.research_state_input_manifests WHERE publication_id=f->>'publication_id' AND manifest_kind='FACT_PUBLICATION';
                IF source_manifest IS NULL OR source_manifest#>ARRAY['fields',field_name] IS DISTINCT FROM f-'publication_id' OR
                   source_manifest->>'entity_id' IS DISTINCT FROM NEW.entity_id OR source_manifest->>'entity_type' IS DISTINCT FROM NEW.entity_type OR
                   source_manifest->>'calendar_publication_id' IS DISTINCT FROM NEW.calendar_publication_id THEN RAISE EXCEPTION 'STATE_FIELD_TRUSTED_PUBLICATION_MISMATCH'; END IF;
            END IF;
            expected_index=CASE WHEN policy.time_role='T' THEN NEW.session_index ELSE NEW.session_index-1 END;
            IF f#>>'{source_field_payload,session_index}' IS DISTINCT FROM expected_index::text OR
               (policy.time_role='T' AND f#>>'{source_field_payload,trade_date}' IS DISTINCT FROM NEW.trade_date::text) THEN
                RAISE EXCEPTION 'STATE_FIELD_TIME_ROLE_MISMATCH';
            END IF;
            IF NEW.payload->>'mode'='ACCEPTED_FACT_INTERFACE' AND
               (f->>'system_available_at' IS NULL OR (f->>'system_available_at')::timestamptz>(NEW.payload->>'cutoff')::timestamptz OR
                NOT EXISTS (SELECT 1 FROM jsonb_array_elements(cal->'sessions') s WHERE s->>'session_index'=expected_index::text AND s->>'trade_date'=f#>>'{source_field_payload,trade_date}')) THEN
                RAISE EXCEPTION 'STATE_FIELD_AVAILABILITY_MISMATCH';
            END IF;
        ELSE RAISE EXCEPTION 'STATE_FIELD_STATUS_INVALID';
        END IF;
    END LOOP;
    IF NEW.payload->>'mode'='ACCEPTED_FACT_INTERFACE' THEN
        SELECT manifest INTO cal FROM v4.research_state_input_manifests WHERE publication_id=NEW.calendar_publication_id AND manifest_kind='MARKET_CALENDAR';
        IF cal IS NULL OR cal->>'lineage_id' IS DISTINCT FROM NEW.calendar_lineage_id OR v4.state_digest_r1_1(cal) IS DISTINCT FROM NEW.calendar_manifest_digest OR
           cal->>'producer_contract_id' IS DISTINCT FROM 'MARKET_CALENDAR_V1' OR
           NOT EXISTS (SELECT 1 FROM jsonb_array_elements(cal->'sessions') s WHERE s->>'trade_date'=NEW.trade_date::text AND s->>'session_index'=NEW.session_index::text) THEN
            RAISE EXCEPTION 'STATE_CALENDAR_LINEAGE_MISMATCH';
        END IF;
        binding=NEW.prior_state_binding;
        IF binding<>'null'::jsonb THEN
            SELECT r.payload INTO prior_row FROM v4.research_state_engineering_results r JOIN v4.research_state_engineering_publications p USING(publication_id)
            WHERE r.publication_id=binding->>'engineering_publication_id' AND r.state_publication_id=binding->>'publication_id' AND
                r.payload_digest=binding->>'payload_digest' AND p.consumer_contract_id=binding->>'consumer_contract_id' AND
                p.model_contract_id=binding->>'model_contract_id' AND p.parameter_set_id=binding->>'parameter_set_id';
            IF prior_row IS NULL OR binding->>'ledger_id'<>'V4_10_ENGINEERING_LEDGER_R1_1' OR prior_row->>'mode'<>'ACCEPTED_FACT_INTERFACE' OR
               prior_row->>'entity_id' IS DISTINCT FROM NEW.entity_id OR prior_row->>'entity_type' IS DISTINCT FROM NEW.entity_type OR
               prior_row->'calendar_binding' IS DISTINCT FROM NEW.payload->'calendar_binding' OR
               (prior_row->>'session_index')::integer>NEW.session_index OR
               ((prior_row->>'session_index')::integer=NEW.session_index AND prior_row->>'trade_date'<>NEW.trade_date::text) THEN RAISE EXCEPTION 'STATE_PRIOR_LEDGER_LINEAGE_MISMATCH'; END IF;
        END IF;
        IF NEW.boundary_event<>'null'::jsonb THEN
            boundary=NEW.boundary_event->'authorized_manifest';
            SELECT manifest INTO source_manifest FROM v4.research_state_input_manifests WHERE publication_id=boundary->>'publication_id' AND manifest_kind='MODEL_BOUNDARY';
            IF source_manifest IS NULL OR source_manifest->>'authorization'<>'AUTHORIZED_ENGINEERING_INTERFACE' OR
               v4.state_digest_r1_1(source_manifest) IS DISTINCT FROM boundary->>'migration_manifest_sha256' OR
               boundary->>'boundary_contract_id' IS DISTINCT FROM 'V4_10_MODEL_BOUNDARY_V1' OR
               EXISTS (SELECT 1 FROM unnest(ARRAY['boundary_contract_id','migration_manifest_id','from_model_contract_id','from_parameter_set_id','to_model_contract_id','to_parameter_set_id','effective_trade_date']) k
                       WHERE source_manifest->k IS DISTINCT FROM boundary->k) OR
               boundary->>'status'<>'AUTHORIZED' OR boundary->>'from_model_contract_id' IS DISTINCT FROM prior_row->>'model_contract_id' OR
               boundary->>'from_parameter_set_id' IS DISTINCT FROM prior_row->>'parameter_set_id' OR
               boundary->>'to_model_contract_id' IS DISTINCT FROM NEW.model_contract_id OR boundary->>'to_parameter_set_id' IS DISTINCT FROM NEW.parameter_set_id OR
               boundary->>'effective_trade_date' IS DISTINCT FROM NEW.trade_date::text THEN RAISE EXCEPTION 'STATE_BOUNDARY_AUTHORIZATION_MISMATCH'; END IF;
        END IF;
    ELSIF NEW.payload->>'mode'<>'SYNTHETIC_CONTRACT_VECTOR' THEN RAISE EXCEPTION 'STATE_MODE_INVALID';
    END IF;
    RETURN NEW;
END $$;

DROP OWNED BY v4_10_reducer_publisher_r1_2,v4_10_state_reader_r1_2;
DROP ROLE v4_10_reducer_publisher_r1_2;
DROP ROLE v4_10_state_reader_r1_2;
