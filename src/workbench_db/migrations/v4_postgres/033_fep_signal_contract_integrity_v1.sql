-- Allocated by V4_MIGRATION_ALLOCATION_REGISTRY_R4. 028--032 remain immutable.
ALTER TABLE fep.observations ADD CONSTRAINT observation_signal_contract_fk
 FOREIGN KEY(core_signal_contract_id) REFERENCES fep.contracts(contract_id);
CREATE TABLE fep.signal_contract_registry (
 contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 scope_id text NOT NULL REFERENCES fep.scopes(scope_id), signal_family text NOT NULL,
 contract_family text NOT NULL, contract_digest fep.sha256 NOT NULL, predicate_digest fep.sha256 NOT NULL,
 PRIMARY KEY(contract_id,scope_id,signal_family)
);
CREATE FUNCTION fep.signal_registry_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c fep.contracts;
BEGIN
 SELECT * INTO STRICT c FROM fep.contracts WHERE contract_id=NEW.contract_id;
 IF c.family IS DISTINCT FROM NEW.contract_family OR c.digest IS DISTINCT FROM NEW.contract_digest
 OR c.body->'accepted_contract'->>'observation_scope' IS DISTINCT FROM NEW.scope_id
 OR c.body->'accepted_contract'->>'contract_id' IS DISTINCT FROM NEW.contract_id
 OR NOT COALESCE((c.body->'accepted_contract'->'formal_signals') ? NEW.signal_family,false)
 OR c.body->>'predicate_digest' IS DISTINCT FROM NEW.predicate_digest
 THEN RAISE EXCEPTION 'FEP_SIGNAL_REGISTRY_SEMANTIC_MISMATCH'; END IF;
 IF NEW.signal_family='FIRST_PREWATCH' AND
 (NEW.contract_id<>'FEP_E2_ENTRY_EVENT_STRATA_V1_1'
 OR NEW.contract_family<>'FEP_E2_ENTRY_EVENT_STRATA_V1_1'
 OR NEW.scope_id<>'FEP_STOCK_ENTRY_CORE'
 OR NEW.contract_digest<>'6df0c6ad8f0109b6a02b56b4f905341cd12b53b3607c18791b3aada285b6d569'
 OR NEW.predicate_digest<>'efe81c599fc24dae00bd7f3e073e389eee2efda242294186010bceb643601b4b'
 OR c.body->'source_binding'->>'sha256' IS DISTINCT FROM '9884d9df4530ceea9ee3268c30e5dfb65ef149939710eb87e66d73466408025a'
 OR c.body->'accepted_contract'->>'contract_id' IS DISTINCT FROM 'FEP_E2_ENTRY_EVENT_STRATA_V1_1'
 OR c.body->'accepted_contract'->>'first_prewatch' IS DISTINCT FROM 'Accepted Radar ENROLLED + maturity PREWATCH + no parent episode; initial SEED upgrade is not an ENROLLED event')
 THEN RAISE EXCEPTION 'FEP_FIRST_PREWATCH_EXACT_AUTHORITY_REQUIRED'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER signal_registry_guard BEFORE INSERT ON fep.signal_contract_registry
 FOR EACH ROW EXECUTE FUNCTION fep.signal_registry_guard();
INSERT INTO fep.signal_contract_registry
 SELECT contract_id,'FEP_STOCK_ENTRY_CORE',s,family,digest,body->>'predicate_digest'
 FROM fep.contracts CROSS JOIN LATERAL jsonb_array_elements_text(body->'accepted_contract'->'formal_signals') s
 WHERE contract_id='FEP_E2_ENTRY_EVENT_STRATA_V1_1';
CREATE FUNCTION fep.observation_signal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM fep.signal_contract_registry r JOIN fep.contracts c USING(contract_id)
 WHERE r.contract_id=NEW.core_signal_contract_id AND r.scope_id=NEW.scope_id
 AND r.signal_family=split_part(NEW.signal_key,':',1) AND c.family=r.contract_family AND c.digest=r.contract_digest)
 THEN RAISE EXCEPTION 'FEP_OBSERVATION_SIGNAL_AUTHORITY_MISMATCH'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER observation_signal_guard BEFORE INSERT OR UPDATE ON fep.observations
 FOR EACH ROW EXECUTE FUNCTION fep.observation_signal_guard();
CREATE FUNCTION fep.signal_registry_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'IMMUTABLE_SIGNAL_REGISTRY'; END $$;
CREATE TRIGGER signal_registry_no_update BEFORE UPDATE OR DELETE ON fep.signal_contract_registry
 FOR EACH ROW EXECUTE FUNCTION fep.signal_registry_immutable();
ALTER TABLE fep.signal_contract_registry OWNER TO fep_schema_owner;
GRANT SELECT ON fep.signal_contract_registry TO fep_application,fep_adapter,fep_auditor;
DO $$ DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['signal_registry_guard','observation_signal_guard','signal_registry_immutable'] LOOP
  EXECUTE format('ALTER FUNCTION fep.%I() OWNER TO fep_schema_owner',n);
  EXECUTE format('ALTER FUNCTION fep.%I() SET search_path=pg_catalog,fep',n);
  EXECUTE format('REVOKE ALL ON FUNCTION fep.%I() FROM PUBLIC',n);
 END LOOP;
END $$;
