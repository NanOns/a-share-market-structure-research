DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM v4.stock_prewatch_publications WHERE consumer_contract_id<>'V4_09_PRIORITY_PROVENANCE_AND_IMMUTABILITY_R1_1') OR
       EXISTS (SELECT 1 FROM v4.stock_prewatch_results WHERE consumer_contract_id<>'V4_09_PRIORITY_PROVENANCE_AND_IMMUTABILITY_R1_1') THEN
        RAISE EXCEPTION 'CONSUMER_IDENTITY_ROLLBACK_WOULD_LOSE_NONLEGACY_GOVERNANCE';
    END IF;
END $$;
DROP TRIGGER v4_stock_prewatch_consumer_identity ON v4.stock_prewatch_results;
DROP FUNCTION v4.guard_stock_prewatch_consumer_identity();
ALTER TABLE v4.stock_prewatch_results DROP CONSTRAINT fk_stock_prewatch_result_consumer,
    DROP COLUMN consumer_contract_id;
ALTER TABLE v4.stock_prewatch_publications DROP CONSTRAINT uq_stock_prewatch_publication_consumer,
    DROP CONSTRAINT ck_stock_prewatch_consumer_id, DROP COLUMN consumer_contract_id;
DELETE FROM v4_meta.schema_migrations WHERE version='V4_STAGE_025_V4_09_CONSUMER_IDENTITY_HARDENING';
