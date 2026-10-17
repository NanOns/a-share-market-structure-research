BEGIN;

-- Draft rollback for R21-R4 contract registry migration only.
-- Execute only after independently confirming the migration is the sole owner
-- of these objects. This intentionally refuses to discard registry history or
-- any accepted publication binding.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM v4.contract_versions LIMIT 1)
       OR EXISTS (SELECT 1 FROM v4.contract_approval_events LIMIT 1)
       OR EXISTS (SELECT 1 FROM v4.publications WHERE contract_bindings IS NOT NULL LIMIT 1) THEN
        RAISE EXCEPTION 'V4_CONTRACT_REGISTRY_ROLLBACK_REFUSED_DATA_PRESENT';
    END IF;
END $$;

DROP TRIGGER IF EXISTS publication_contract_bindings_guard ON v4.publications;
DROP FUNCTION IF EXISTS v4.validate_publication_contract_bindings();
ALTER TABLE v4.publications
    DROP CONSTRAINT IF EXISTS ck_accepted_publication_has_contract_bindings;
ALTER TABLE v4.publications DROP COLUMN IF EXISTS contract_bindings;

DROP TRIGGER IF EXISTS contract_versions_no_truncate ON v4.contract_versions;
DROP TRIGGER IF EXISTS contract_versions_recorded_at ON v4.contract_versions;
DROP TRIGGER IF EXISTS contract_versions_append_only ON v4.contract_versions;
DROP TRIGGER IF EXISTS contract_approval_events_no_truncate ON v4.contract_approval_events;
DROP TRIGGER IF EXISTS contract_approval_events_recorded_at ON v4.contract_approval_events;
DROP TRIGGER IF EXISTS contract_approval_events_append_only ON v4.contract_approval_events;
DROP FUNCTION IF EXISTS v4.stamp_contract_registry_recorded_at();
DROP FUNCTION IF EXISTS v4.reject_contract_registry_truncate();
DROP FUNCTION IF EXISTS v4.reject_contract_approval_event_mutation();
DROP FUNCTION IF EXISTS v4.reject_contract_version_mutation();
DROP TABLE v4.contract_approval_events;
DROP TABLE v4.contract_versions;

COMMIT;
