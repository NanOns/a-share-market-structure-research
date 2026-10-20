-- Keep owner_schema as immutable source provenance after physical migration.
-- The locator is resolved only through the exact v4 migration receipt and the
-- family-specific sealed Owner version stored in fixed v4 relations.
CREATE OR REPLACE FUNCTION v4.guard_publication_module_result_r4()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    p v4.publications%ROWTYPE;
    family_name text;
    receipt record;
    owner_matches boolean := false;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('v4-module-results:' || NEW.publication_id, 0));
    SELECT * INTO STRICT p FROM v4.publications WHERE publication_id = NEW.publication_id;
    IF p.status IS DISTINCT FROM 'ACCEPTED' OR p.accepted_at IS NULL THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_PUBLICATION_NOT_ACCEPTED';
    END IF;
    IF NEW.owner_trade_date IS DISTINCT FROM p.trade_date THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_T0_MISMATCH';
    END IF;
    IF NEW.module_contract_id IS DISTINCT FROM 'V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R4' THEN
        RAISE EXCEPTION 'V4_MODULE_CONTRACT_ID_MISMATCH';
    END IF;
    IF NEW.database_identity->>'database' IS DISTINCT FROM current_database()
       OR NEW.database_identity->>'database_oid' IS DISTINCT FROM
          (SELECT oid::text FROM pg_database WHERE datname = current_database()) THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_DATABASE_MISMATCH';
    END IF;
    IF NEW.owner_schema !~ '^v4_[a-f0-9]{56}$' THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_SOURCE_SCHEMA_INVALID';
    END IF;
    family_name := CASE NEW.module_key
        WHEN 'research_priority' THEN 'research_priority'
        WHEN 'operational_risk' THEN 'operational_risk'
        WHEN 'sector_lifecycle' THEN 'sector_lifecycle'
        ELSE NULL
    END;
    IF family_name IS NULL THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_FAMILY_INVALID';
    END IF;
    SELECT digest, contract, row_count, verification INTO receipt
      FROM v4.owner_schema_migration_map_r1
     WHERE family = family_name
       AND source_schema = NEW.owner_schema
       AND token = NEW.owner_version_token
       AND T0 = NEW.owner_trade_date::text;
    IF NOT FOUND OR receipt.digest IS DISTINCT FROM NEW.result_digest
       OR receipt.contract IS DISTINCT FROM NEW.owner_contract_id
       OR receipt.row_count IS DISTINCT FROM NEW.row_count
       OR receipt.verification->>'status' IS DISTINCT FROM 'VERIFIED' THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_MIGRATION_RECEIPT_MISSING_OR_MISMATCH';
    END IF;
    IF family_name = 'research_priority' THEN
        SELECT EXISTS (
            SELECT 1 FROM v4.owner_versions_priority_r1 o
             WHERE o.token = NEW.owner_version_token AND o.T0 = NEW.owner_trade_date::text
               AND o.digest = NEW.result_digest AND o.contract = NEW.owner_contract_id
               AND o.row_count = NEW.row_count AND o.sealed
               AND o.database_identity = NEW.database_identity
        ) INTO owner_matches;
    ELSIF family_name = 'operational_risk' THEN
        SELECT EXISTS (
            SELECT 1 FROM v4.owner_versions_risk_r1 o
             WHERE o.token = NEW.owner_version_token AND o.T0 = NEW.owner_trade_date::text
               AND o.digest = NEW.result_digest AND o.contract = NEW.owner_contract_id
               AND o.row_count = NEW.row_count AND o.sealed
               AND o.database_identity = NEW.database_identity
        ) INTO owner_matches;
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM v4.sector_lifecycle_owner_versions_r1 o
             WHERE o.token = NEW.owner_version_token AND o.T0 = NEW.owner_trade_date::text
               AND o.digest = NEW.result_digest AND o.contract = NEW.owner_contract_id
               AND o.row_count = NEW.row_count AND o.sealed
               AND o.database_identity = NEW.database_identity
        ) INTO owner_matches;
    END IF;
    IF NOT owner_matches THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_SINGLE_SCHEMA_VERSION_MISSING_OR_MISMATCH';
    END IF;
    IF EXISTS (SELECT 1 FROM v4.publication_heads WHERE publication_id = NEW.publication_id) THEN
        RAISE EXCEPTION 'V4_PUBLICATION_MODULE_SET_SEALED';
    END IF;
    RETURN NEW;
END $$;
