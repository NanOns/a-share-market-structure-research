-- R14: persist the independently sourced same-T0 Universe and exact Core reconciliation.
-- The legacy publication table's primary key is publication_id. The canonical
-- row identity exposed to publication-bound relations is (publication_id,
-- revision_no), so expose that exact key for downstream foreign keys as well.
CREATE UNIQUE INDEX IF NOT EXISTS uq_publications_publication_revision
    ON v4.publications (publication_id, revision_no);

CREATE TABLE v4.market_universe_snapshots (
    publication_id text NOT NULL,
    publication_revision integer NOT NULL CHECK (publication_revision > 0),
    trade_date date NOT NULL,
    source_manifest_sha256 char(64) NOT NULL CHECK (source_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    source_package_id text NOT NULL REFERENCES v4.source_packages(package_id),
    acceptance_receipt_id text NOT NULL,
    acceptance_receipt_sha256 char(64) NOT NULL CHECK (acceptance_receipt_sha256 ~ '^[0-9a-f]{64}$'),
    acceptance_authority_id text NOT NULL CHECK (btrim(acceptance_authority_id) <> ''),
    source_fact_sha256 char(64) NOT NULL CHECK (source_fact_sha256 ~ '^[0-9a-f]{64}$'),
    logical_fact_id text NOT NULL,
    fact_digest char(64) NOT NULL CHECK (fact_digest ~ '^[0-9a-f]{64}$'),
    raw_artifact_sha256 char(64) NOT NULL CHECK (raw_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    universe_id text NOT NULL CHECK (btrim(universe_id) <> ''),
    universe_contract_id text NOT NULL,
    universe_contract_version text NOT NULL,
    universe_sha256 char(64) NOT NULL CHECK (universe_sha256 ~ '^[0-9a-f]{64}$'),
    exchange_scope text[] NOT NULL CHECK (array_length(exchange_scope,1) = 3),
    expected_count integer NOT NULL CHECK (expected_count > 0),
    core_count integer NOT NULL CHECK (core_count > 0),
    coverage_ratio double precision NOT NULL CHECK (coverage_ratio = 1.0),
    reconciliation_sha256 char(64) NOT NULL CHECK (reconciliation_sha256 ~ '^[0-9a-f]{64}$'),
    category_counts jsonb NOT NULL,
    persistence_identity_sha256 char(64) NOT NULL UNIQUE CHECK (persistence_identity_sha256 ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status = 'PASS'),
    captured_at timestamptz NOT NULL,
    PRIMARY KEY (publication_id, publication_revision),
    FOREIGN KEY (publication_id, publication_revision)
        REFERENCES v4.publications(publication_id, revision_no),
    CHECK (universe_contract_id = 'V4_MARKET_UNIVERSE_COMPLETENESS_R1'),
    CHECK (universe_contract_version = '1.0.0'),
    CHECK (expected_count = core_count)
);

CREATE TABLE v4.market_universe_snapshot_rows (
    publication_id text NOT NULL,
    publication_revision integer NOT NULL,
    security_id text NOT NULL CHECK (btrim(security_id) <> ''),
    asset_class text NOT NULL,
    share_class text NOT NULL,
    exchange text NOT NULL,
    status text NOT NULL,
    source_id text NOT NULL CHECK (btrim(source_id) <> ''),
    PRIMARY KEY (publication_id, publication_revision, security_id),
    FOREIGN KEY (publication_id, publication_revision)
        REFERENCES v4.market_universe_snapshots(publication_id, publication_revision)
);

CREATE TABLE v4.market_universe_reconciliation_rows (
    publication_id text NOT NULL,
    publication_revision integer NOT NULL,
    security_id text NOT NULL CHECK (btrim(security_id) <> ''),
    source_present boolean NOT NULL,
    core_present boolean NOT NULL,
    expected_in_denominator boolean NOT NULL,
    category text NOT NULL,
    asset_class text,
    share_class text,
    exchange text,
    status text NOT NULL,
    source_id text NOT NULL,
    PRIMARY KEY (publication_id, publication_revision, security_id),
    FOREIGN KEY (publication_id, publication_revision)
        REFERENCES v4.market_universe_snapshots(publication_id, publication_revision)
);

CREATE FUNCTION v4.reject_market_universe_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_MARKET_UNIVERSE_SNAPSHOT_APPEND_ONLY';
END $$;

CREATE FUNCTION v4.require_universe_source_fact()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source_fact v4.source_package_facts%ROWTYPE;
DECLARE package_scope text;
BEGIN
    SELECT * INTO STRICT source_fact FROM v4.source_package_facts
     WHERE package_id=NEW.source_package_id AND source_key='security_universe'
       AND logical_fact_id=NEW.logical_fact_id AND fact_digest=NEW.fact_digest;
    SELECT accepted_scope INTO STRICT package_scope FROM v4.source_packages
     WHERE package_id=NEW.source_package_id;
    IF package_scope <> 'ACCEPTED_SOURCE_PACKAGE'
       OR source_fact.source_fact_sha256 <> NEW.source_fact_sha256
       OR source_fact.acceptance_receipt_id <> NEW.acceptance_receipt_id
       OR source_fact.record_locator->>'universe_id' <> NEW.universe_id
       OR source_fact.record_locator->>'universe_sha256' <> NEW.universe_sha256 THEN
        RAISE EXCEPTION 'V4_MARKET_UNIVERSE_SOURCE_FACT_BINDING_INVALID';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER market_universe_source_fact_guard
    BEFORE INSERT ON v4.market_universe_snapshots
    FOR EACH ROW EXECUTE FUNCTION v4.require_universe_source_fact();

CREATE TRIGGER market_universe_snapshots_immutable
    BEFORE UPDATE OR DELETE ON v4.market_universe_snapshots
    FOR EACH ROW EXECUTE FUNCTION v4.reject_market_universe_mutation();
CREATE TRIGGER market_universe_snapshots_no_truncate
    BEFORE TRUNCATE ON v4.market_universe_snapshots
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_market_universe_mutation();
CREATE TRIGGER market_universe_snapshot_rows_immutable
    BEFORE UPDATE OR DELETE ON v4.market_universe_snapshot_rows
    FOR EACH ROW EXECUTE FUNCTION v4.reject_market_universe_mutation();
CREATE TRIGGER market_universe_snapshot_rows_no_truncate
    BEFORE TRUNCATE ON v4.market_universe_snapshot_rows
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_market_universe_mutation();
CREATE TRIGGER market_universe_reconciliation_rows_immutable
    BEFORE UPDATE OR DELETE ON v4.market_universe_reconciliation_rows
    FOR EACH ROW EXECUTE FUNCTION v4.reject_market_universe_mutation();
CREATE TRIGGER market_universe_reconciliation_rows_no_truncate
    BEFORE TRUNCATE ON v4.market_universe_reconciliation_rows
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_market_universe_mutation();

CREATE FUNCTION v4.verify_market_universe_rowset()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE snapshot_count integer;
DECLARE reconciliation_count integer;
DECLARE accepted_source_count integer;
BEGIN
    SELECT count(*) INTO snapshot_count FROM v4.market_universe_snapshot_rows
     WHERE publication_id=NEW.publication_id AND publication_revision=NEW.publication_revision;
    SELECT count(*) INTO reconciliation_count FROM v4.market_universe_reconciliation_rows
     WHERE publication_id=NEW.publication_id AND publication_revision=NEW.publication_revision;
    SELECT record_count INTO STRICT accepted_source_count FROM v4.source_package_facts
     WHERE package_id=NEW.source_package_id AND source_key='security_universe'
       AND logical_fact_id=NEW.logical_fact_id AND fact_digest=NEW.fact_digest;
    IF snapshot_count <> accepted_source_count OR snapshot_count = 0 OR reconciliation_count = 0 THEN
        RAISE EXCEPTION 'V4_MARKET_UNIVERSE_ROWSET_NOT_COMPLETE';
    END IF;
    RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER market_universe_snapshot_rowset_guard
    AFTER INSERT ON v4.market_universe_snapshots DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION v4.verify_market_universe_rowset();

CREATE OR REPLACE FUNCTION v4.require_universe_for_accepted_publication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status='ACCEPTED' AND NEW.trade_date >= DATE '2026-10-16'
       AND NOT EXISTS (
          SELECT 1 FROM v4.market_universe_snapshots u
           WHERE u.publication_id=NEW.publication_id AND u.publication_revision=NEW.revision_no
             AND u.trade_date=NEW.trade_date
             AND u.source_manifest_sha256=NEW.source_manifest_sha256
             AND u.status='PASS' AND u.coverage_ratio=1.0
       ) THEN
        RAISE EXCEPTION 'V4_ACCEPTED_PUBLICATION_REQUIRES_VERIFIED_UNIVERSE';
    END IF;
    RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER accepted_publication_requires_universe
    AFTER INSERT OR UPDATE ON v4.publications DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION v4.require_universe_for_accepted_publication();
