-- FEP_E5_ENGINEERING_LEDGER_V1. Explicit isolated engineering namespace, not production migration.
CREATE SCHEMA IF NOT EXISTS fep_e5_engineering;
CREATE TABLE IF NOT EXISTS fep_e5_engineering.models(
 id text PRIMARY KEY, scope text NOT NULL, observation_scope text NOT NULL, target text NOT NULL,
 horizon text NOT NULL, feature text NOT NULL, namespace text NOT NULL, payload jsonb NOT NULL,
 UNIQUE(id,scope,observation_scope,target,horizon,feature,namespace));
CREATE TABLE IF NOT EXISTS fep_e5_engineering.prediction_slots(
 id text PRIMARY KEY, scope text NOT NULL, observation_scope text NOT NULL, target text NOT NULL,
 horizon text NOT NULL, feature text NOT NULL, namespace text NOT NULL, payload jsonb NOT NULL,
 UNIQUE(id,scope,observation_scope,target,horizon,feature,namespace));
CREATE TABLE IF NOT EXISTS fep_e5_engineering.slot_model_bindings(
 id text PRIMARY KEY REFERENCES fep_e5_engineering.prediction_slots(id), model_id text NOT NULL,
 scope text NOT NULL, observation_scope text NOT NULL, target text NOT NULL, horizon text NOT NULL, feature text NOT NULL, namespace text NOT NULL,
 payload jsonb NOT NULL,
 FOREIGN KEY(id,scope,observation_scope,target,horizon,feature,namespace) REFERENCES fep_e5_engineering.prediction_slots(id,scope,observation_scope,target,horizon,feature,namespace),
 FOREIGN KEY(model_id,scope,observation_scope,target,horizon,feature,namespace) REFERENCES fep_e5_engineering.models(id,scope,observation_scope,target,horizon,feature,namespace));
CREATE TABLE IF NOT EXISTS fep_e5_engineering.permission_keys(
 id text PRIMARY KEY, model_id text NOT NULL REFERENCES fep_e5_engineering.models(id), capability text NOT NULL CHECK(capability='SHADOW_INFERENCE'),payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.prediction_runs(
 id text PRIMARY KEY, slot_id text NOT NULL REFERENCES fep_e5_engineering.slot_model_bindings(id),payload jsonb NOT NULL,UNIQUE(id,slot_id));
CREATE TABLE IF NOT EXISTS fep_e5_engineering.predictions(
 id text PRIMARY KEY, slot_id text NOT NULL REFERENCES fep_e5_engineering.slot_model_bindings(id),run_id text NOT NULL,revision integer NOT NULL CHECK(revision>0),
 supersedes text REFERENCES fep_e5_engineering.predictions(id),payload jsonb NOT NULL,UNIQUE(slot_id,revision),
 FOREIGN KEY(run_id,slot_id) REFERENCES fep_e5_engineering.prediction_runs(id,slot_id));
CREATE TABLE IF NOT EXISTS fep_e5_engineering.projections(id text PRIMARY KEY REFERENCES fep_e5_engineering.predictions(id),payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.slot_receipts(id text PRIMARY KEY,slot_id text NOT NULL REFERENCES fep_e5_engineering.prediction_slots(id),payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.acceptance_receipts(id text PRIMARY KEY,run_id text NOT NULL REFERENCES fep_e5_engineering.prediction_runs(id),grant_id text NOT NULL REFERENCES fep_e5_engineering.permission_keys(id),payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.activations(id text PRIMARY KEY,grant_id text NOT NULL REFERENCES fep_e5_engineering.permission_keys(id),payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.deployment_receipts(id text PRIMARY KEY,payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.deployment_heads(id text PRIMARY KEY,version integer NOT NULL CHECK(version>0),payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.priority_projection(id text PRIMARY KEY,payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS fep_e5_engineering.protocols(id text PRIMARY KEY,payload jsonb NOT NULL);
CREATE OR REPLACE FUNCTION fep_e5_engineering.immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'E5_APPEND_ONLY'; END $$;
DO $$ DECLARE tab text; BEGIN
 FOREACH tab IN ARRAY ARRAY['models','prediction_slots','slot_model_bindings','permission_keys','prediction_runs','predictions','projections','slot_receipts','acceptance_receipts','activations','deployment_receipts','priority_projection','protocols'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=format('fep_e5_engineering.%I',tab)::regclass AND tgname='immutable') THEN
   EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep_e5_engineering.%I FOR EACH ROW EXECUTE FUNCTION fep_e5_engineering.immutable()',tab);
  END IF;
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION fep_e5_engineering.head_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' OR current_setting('fep_e5.cas',true) IS DISTINCT FROM 'on' THEN RAISE EXCEPTION 'E5_HEAD_CAS_REQUIRED'; END IF;
 RETURN NEW;
END $$;
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid='fep_e5_engineering.deployment_heads'::regclass AND tgname='head_guard') THEN
  CREATE TRIGGER head_guard BEFORE INSERT OR UPDATE OR DELETE ON fep_e5_engineering.deployment_heads FOR EACH ROW EXECUTE FUNCTION fep_e5_engineering.head_guard();
 END IF;
END $$;
