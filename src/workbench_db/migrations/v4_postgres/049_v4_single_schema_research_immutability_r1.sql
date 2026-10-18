CREATE OR REPLACE FUNCTION v4.guard_research_release_immutability()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    release_key text;
    release_sealed boolean;
BEGIN
    IF TG_TABLE_NAME='research_releases' THEN
        IF TG_OP='INSERT' AND NEW.sealed THEN
            RAISE EXCEPTION 'RESEARCH_RELEASE_MUST_BE_BUILT_BEFORE_SEAL';
        END IF;
        IF TG_OP IN ('UPDATE','DELETE') AND OLD.sealed THEN
            RAISE EXCEPTION 'IMMUTABLE_RESEARCH_RELEASE';
        END IF;
    ELSE
        IF TG_TABLE_NAME='legacy_schema_migration_map' THEN
            release_key := CASE WHEN TG_OP='DELETE' THEN OLD.canonical_version ELSE NEW.canonical_version END;
        ELSE
            release_key := CASE WHEN TG_OP='DELETE' THEN OLD.release_id ELSE NEW.release_id END;
        END IF;
        SELECT sealed INTO release_sealed FROM v4.research_releases WHERE release_id=release_key;
        IF release_sealed THEN RAISE EXCEPTION 'IMMUTABLE_RESEARCH_RELEASE_ROWS'; END IF;
        IF TG_OP='UPDATE' THEN
            IF TG_TABLE_NAME='legacy_schema_migration_map' THEN
                release_key := OLD.canonical_version;
            ELSE
                release_key := OLD.release_id;
            END IF;
            SELECT sealed INTO release_sealed FROM v4.research_releases WHERE release_id=release_key;
            IF release_sealed THEN RAISE EXCEPTION 'IMMUTABLE_RESEARCH_RELEASE_ROWS'; END IF;
        END IF;
    END IF;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;

CREATE OR REPLACE FUNCTION v4.reject_research_release_truncate()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'RESEARCH_RELEASE_TRUNCATE_FORBIDDEN';
END $$;

DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'research_releases','research_objects','research_aliases','research_members',
        'research_metadata','research_series_versions','research_series_bars',
        'research_journal_versions','research_journal_days','research_journal_inputs',
        'legacy_schema_migration_map'
    ] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS research_release_immutable ON v4.%I',relation_name);
        EXECUTE format('DROP TRIGGER IF EXISTS research_release_no_truncate ON v4.%I',relation_name);
        EXECUTE format('CREATE TRIGGER research_release_immutable BEFORE INSERT OR UPDATE OR DELETE ON v4.%I FOR EACH ROW EXECUTE FUNCTION v4.guard_research_release_immutability()',relation_name);
        EXECUTE format('CREATE TRIGGER research_release_no_truncate BEFORE TRUNCATE ON v4.%I FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_research_release_truncate()',relation_name);
    END LOOP;
END $$;
