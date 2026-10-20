-- R7 repair of the R6 proposal: publication_id is the physical publication
-- identity and revision_no is its declared sequence. This is still a DDL
-- proposal only; it has not been executed or compatibility-tested in live PG.

CREATE TABLE v4.daily_core_result_snapshots (
    publication_id text NOT NULL,
    publication_revision integer NOT NULL,
    trade_date date NOT NULL,
    result_identity text NOT NULL,
    result_contract_id text NOT NULL,
    producer_contract_id text NOT NULL,
    producer_sha256 char(64) NOT NULL,
    producer_receipt_sha256 char(64) NOT NULL,
    source_manifest_sha256 char(64) NOT NULL,
    result_sha256 char(64) NOT NULL,
    row_count integer NOT NULL CHECK (row_count > 0),
    missing_price_rows integer NOT NULL CHECK (missing_price_rows >= 0 AND missing_price_rows <= row_count),
    completeness_contract_id text NOT NULL,
    completeness_contract_version text NOT NULL,
    completeness_status text NOT NULL CHECK (completeness_status IN ('CONTRACT_UNRESOLVED','PASS','FAIL')),
    quality_status text NOT NULL,
    captured_at timestamptz NOT NULL,
    PRIMARY KEY (publication_id, publication_revision),
    UNIQUE (result_identity),
    FOREIGN KEY (publication_id)
        REFERENCES v4.publications(publication_id),
    CHECK (producer_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (producer_receipt_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (source_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (result_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (btrim(result_identity) <> '' AND btrim(producer_contract_id) <> ''),
    CHECK (completeness_status <> 'PASS' OR (completeness_contract_id <> 'UNRESOLVED' AND completeness_contract_version <> 'UNRESOLVED'))
);

CREATE TABLE v4.daily_core_result_rows (
    publication_id text NOT NULL,
    publication_revision integer NOT NULL,
    trade_date date NOT NULL,
    security_id text NOT NULL,
    security_type text NOT NULL,
    trade_status text NOT NULL,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision,
    amount double precision,
    turnover_rate double precision,
    turnover_status text NOT NULL CHECK (turnover_status IN ('AVAILABLE','TURNOVER_UNAVAILABLE')),
    ma5 double precision,
    ma20 double precision,
    ma60 double precision,
    history_status text NOT NULL CHECK (history_status IN ('SUFFICIENT','INSUFFICIENT_NEW_LISTING_HISTORY','HISTORY_UNKNOWN')),
    price_basis text NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    profile_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    quality_status text NOT NULL,
    row_sha256 char(64) NOT NULL,
    PRIMARY KEY (publication_id, publication_revision, security_id),
    FOREIGN KEY (publication_id, publication_revision)
        REFERENCES v4.daily_core_result_snapshots(publication_id, publication_revision),
    CHECK (btrim(security_id) <> '' AND btrim(security_type) <> ''),
    CHECK (trade_status IN ('TRADING','SUSPENDED','DELISTED','UNKNOWN')),
    CHECK (price_basis = 'TDX_GBBQ_UNCHANGED'),
    CHECK (row_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK ((open IS NULL OR open >= 0) AND (high IS NULL OR high >= 0)
       AND (low IS NULL OR low >= 0) AND (close IS NULL OR close >= 0)
       AND (volume IS NULL OR volume >= 0) AND (amount IS NULL OR amount >= 0)
       AND (turnover_rate IS NULL OR turnover_rate >= 0)),
    CHECK ((turnover_status='AVAILABLE' AND turnover_rate IS NOT NULL)
       OR (turnover_status='TURNOVER_UNAVAILABLE' AND turnover_rate IS NULL)),
    CHECK ((trade_status <> 'TRADING') OR (open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL))
);

CREATE OR REPLACE FUNCTION v4.require_core_row_consumed_tdx_revision()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM v4.publication_consumed_sources cs
        JOIN v4.publications p ON p.publication_id=cs.publication_id
         WHERE cs.publication_id=NEW.publication_id
           AND p.revision_no=NEW.publication_revision
           AND cs.source_revision_id=NEW.source_revision_id
           AND cs.source_key='tdx'
    ) THEN
        RAISE EXCEPTION 'V4_CORE_ROW_TDX_REVISION_NOT_CONSUMED_BY_PUBLICATION';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER daily_core_result_row_tdx_source_guard
    BEFORE INSERT ON v4.daily_core_result_rows
    FOR EACH ROW EXECUTE FUNCTION v4.require_core_row_consumed_tdx_revision();

CREATE OR REPLACE FUNCTION v4.reject_daily_core_result_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_DAILY_CORE_RESULT_APPEND_ONLY';
END $$;

CREATE TRIGGER daily_core_result_snapshots_immutable
    BEFORE UPDATE OR DELETE ON v4.daily_core_result_snapshots
    FOR EACH ROW EXECUTE FUNCTION v4.reject_daily_core_result_mutation();
CREATE TRIGGER daily_core_result_rows_immutable
    BEFORE UPDATE OR DELETE ON v4.daily_core_result_rows
    FOR EACH ROW EXECUTE FUNCTION v4.reject_daily_core_result_mutation();
CREATE TRIGGER daily_core_result_snapshots_no_truncate
    BEFORE TRUNCATE ON v4.daily_core_result_snapshots
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_daily_core_result_mutation();
CREATE TRIGGER daily_core_result_rows_no_truncate
    BEFORE TRUNCATE ON v4.daily_core_result_rows
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_daily_core_result_mutation();

CREATE OR REPLACE FUNCTION v4.verify_daily_core_result_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_count integer;
DECLARE missing_count integer;
DECLARE wrong_date_count integer;
DECLARE current_publication v4.publications%ROWTYPE;
BEGIN
    SELECT * INTO STRICT current_publication FROM v4.publications
     WHERE publication_id=NEW.publication_id AND revision_no=NEW.publication_revision;
    IF NEW.trade_date <> current_publication.trade_date
       OR NEW.source_manifest_sha256 <> current_publication.source_manifest_sha256 THEN
        RAISE EXCEPTION 'V4_DAILY_CORE_RESULT_PUBLICATION_IDENTITY_MISMATCH';
    END IF;
    SELECT count(*), count(*) FILTER (WHERE close IS NULL), count(*) FILTER (WHERE trade_date<>NEW.trade_date)
      INTO actual_count, missing_count, wrong_date_count
      FROM v4.daily_core_result_rows
     WHERE publication_id=NEW.publication_id AND publication_revision=NEW.publication_revision;
    IF actual_count <> NEW.row_count OR missing_count <> NEW.missing_price_rows OR wrong_date_count <> 0 THEN
        RAISE EXCEPTION 'V4_DAILY_CORE_RESULT_ROWSET_MISMATCH';
    END IF;
    IF NEW.completeness_status <> 'PASS' THEN
        IF current_publication.status='ACCEPTED' THEN
            RAISE EXCEPTION 'V4_CORE_RESULT_COMPLETENESS_NOT_ACCEPTED';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER daily_core_result_snapshot_rowset_guard
    AFTER INSERT ON v4.daily_core_result_snapshots DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION v4.verify_daily_core_result_snapshot();

CREATE OR REPLACE FUNCTION v4.require_core_result_for_accepted_publication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status='ACCEPTED' AND NOT EXISTS (
        SELECT 1 FROM v4.daily_core_result_snapshots s
         WHERE s.publication_id=NEW.publication_id
           AND s.publication_revision=NEW.revision_no
           AND s.trade_date=NEW.trade_date
           AND s.source_manifest_sha256=NEW.source_manifest_sha256
           AND s.completeness_status='PASS'
           AND s.row_count > 0
    ) THEN
        RAISE EXCEPTION 'V4_ACCEPTED_PUBLICATION_REQUIRES_VERIFIED_CORE_RESULT';
    END IF;
    RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER accepted_publication_requires_core_result
    AFTER INSERT OR UPDATE ON v4.publications DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION v4.require_core_result_for_accepted_publication();
