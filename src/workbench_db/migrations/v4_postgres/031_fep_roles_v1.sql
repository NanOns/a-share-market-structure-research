-- Cluster roles are NOLOGIN, disjoint, and never inherited by the application.
DO $$ DECLARE name text; r record; BEGIN
 FOREACH name IN ARRAY ARRAY['fep_schema_owner','fep_cas_owner','fep_application','fep_deployer','fep_adapter','fep_auditor'] LOOP
  SELECT * INTO r FROM pg_roles WHERE rolname=name;
  IF FOUND THEN
   IF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolcanlogin OR r.rolinherit OR r.rolbypassrls
    OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid OR roleid=r.oid) THEN
    RAISE EXCEPTION 'FEP_ROLE_IDENTITY_CONFLICT:%',name;
   END IF;
  ELSE
   EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',name);
  END IF;
 END LOOP;
END $$;
REVOKE ALL ON SCHEMA fep FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA fep FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA fep FROM PUBLIC;
ALTER SCHEMA fep OWNER TO fep_schema_owner;
ALTER DOMAIN fep.sha256 OWNER TO fep_schema_owner;
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='fep' LOOP
  EXECUTE format('ALTER TABLE fep.%I OWNER TO fep_schema_owner',r.tablename);
 END LOOP;
 FOR r IN SELECT p.oid::regprocedure AS signature FROM pg_proc p
 JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='fep' LOOP
  EXECUTE format('ALTER FUNCTION %s OWNER TO fep_schema_owner',r.signature);
  EXECUTE format('ALTER FUNCTION %s SET search_path=pg_catalog,fep',r.signature);
 END LOOP;
END $$;
GRANT USAGE ON SCHEMA fep TO fep_application,fep_deployer,fep_adapter,fep_auditor,fep_cas_owner;
GRANT USAGE ON SCHEMA v4 TO fep_application,fep_adapter;
GRANT SELECT ON v4.publications,v4.model_namespaces TO fep_application,fep_adapter;
GRANT SELECT ON ALL TABLES IN SCHEMA fep TO fep_application,fep_auditor,fep_adapter;
GRANT INSERT ON fep.observations,fep.observation_revisions,fep.snapshots,fep.feature_values,
 fep.datasets,fep.dataset_eligibility_ledger,fep.dataset_fold_cutoffs,
 fep.dataset_fold_label_selection,fep.dataset_rows,fep.prediction_slots,fep.slot_receipts
 TO fep_application;
GRANT INSERT ON fep.label_source_bindings,fep.label_revisions TO fep_adapter;
GRANT SELECT ON fep.permission_keys,fep.activations,fep.deployment_heads,fep.deployment_change_receipts TO fep_cas_owner;
GRANT INSERT ON fep.activations,fep.deployment_heads,fep.deployment_change_receipts TO fep_cas_owner;
GRANT UPDATE ON fep.deployment_heads TO fep_cas_owner;
ALTER FUNCTION fep.cas_deploy(text,text,text,bigint,text,text,fep.sha256,jsonb) OWNER TO fep_cas_owner;
GRANT EXECUTE ON FUNCTION fep.cas_deploy(text,text,text,bigint,text,text,fep.sha256,jsonb) TO fep_deployer;
-- E2+ structures remain inaccessible for application writes. No actual grant is seeded.
ALTER DEFAULT PRIVILEGES FOR ROLE fep_schema_owner IN SCHEMA fep REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
