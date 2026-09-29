PRAGMA foreign_keys = ON;
CREATE TABLE model_namespaces (
  namespace_id TEXT PRIMARY KEY,
  model_contract_id TEXT NOT NULL,
  execution_mode TEXT NOT NULL CHECK (execution_mode = 'REPLAY'),
  namespace TEXT NOT NULL,
  UNIQUE(model_contract_id, execution_mode, namespace)
);
CREATE TABLE source_revisions (
  source_revision_id TEXT PRIMARY KEY,
  logical_fact_id TEXT NOT NULL,
  revision_no INTEGER NOT NULL CHECK (revision_no > 0),
  digest TEXT NOT NULL,
  payload TEXT NOT NULL,
  supersedes_revision_id TEXT REFERENCES source_revisions(source_revision_id),
  UNIQUE(logical_fact_id, revision_no),
  UNIQUE(supersedes_revision_id)
);
CREATE TABLE publications (
  publication_id TEXT PRIMARY KEY,
  trade_date TEXT NOT NULL,
  model_namespace_id TEXT NOT NULL REFERENCES model_namespaces(namespace_id),
  revision_no INTEGER NOT NULL CHECK (revision_no > 0),
  status TEXT NOT NULL CHECK (status IN ('CANDIDATE','ACCEPTED','RETRACTED','REJECTED')),
  source_manifest_sha256 TEXT NOT NULL,
  computation_identity_sha256 TEXT NOT NULL,
  formal_publication_identity TEXT NOT NULL,
  logical_output_sha256 TEXT NOT NULL,
  parent_publication_id TEXT REFERENCES publications(publication_id),
  UNIQUE(trade_date, model_namespace_id, revision_no),
  UNIQUE(trade_date, model_namespace_id, source_manifest_sha256,
         computation_identity_sha256, formal_publication_identity, logical_output_sha256)
);
CREATE TABLE publication_consumed_sources (
  publication_id TEXT NOT NULL REFERENCES publications(publication_id),
  source_key TEXT NOT NULL,
  source_revision_id TEXT NOT NULL REFERENCES source_revisions(source_revision_id),
  digest TEXT NOT NULL,
  PRIMARY KEY(publication_id, source_key)
);
CREATE TABLE publication_revision_events (
  event_id TEXT PRIMARY KEY,
  publication_id TEXT NOT NULL REFERENCES publications(publication_id),
  event_type TEXT NOT NULL CHECK (event_type IN ('CREATED','ACCEPTED')),
  prior_publication_id TEXT REFERENCES publications(publication_id),
  UNIQUE(publication_id, event_type)
);
CREATE TABLE publication_heads (
  trade_date TEXT NOT NULL,
  model_namespace_id TEXT NOT NULL REFERENCES model_namespaces(namespace_id),
  publication_id TEXT NOT NULL REFERENCES publications(publication_id),
  PRIMARY KEY(trade_date, model_namespace_id)
);
CREATE TRIGGER immutable_publication_update BEFORE UPDATE ON publications
WHEN NOT (OLD.status = 'CANDIDATE' AND NEW.status = 'ACCEPTED'
  AND OLD.publication_id=NEW.publication_id AND OLD.trade_date=NEW.trade_date
  AND OLD.model_namespace_id=NEW.model_namespace_id AND OLD.revision_no=NEW.revision_no
  AND OLD.source_manifest_sha256=NEW.source_manifest_sha256
  AND OLD.computation_identity_sha256=NEW.computation_identity_sha256
  AND OLD.formal_publication_identity=NEW.formal_publication_identity
  AND OLD.logical_output_sha256=NEW.logical_output_sha256
  AND OLD.parent_publication_id IS NEW.parent_publication_id)
BEGIN SELECT RAISE(ABORT, 'PUBLICATION_IDENTITY_IMMUTABLE'); END;
CREATE TRIGGER immutable_publication_delete BEFORE DELETE ON publications
BEGIN SELECT RAISE(ABORT, 'PUBLICATION_APPEND_ONLY'); END;
CREATE TRIGGER immutable_consumed_update BEFORE UPDATE ON publication_consumed_sources
BEGIN SELECT RAISE(ABORT, 'CONSUMED_SOURCE_IMMUTABLE'); END;
CREATE TRIGGER immutable_consumed_delete BEFORE DELETE ON publication_consumed_sources
BEGIN SELECT RAISE(ABORT, 'CONSUMED_SOURCE_APPEND_ONLY'); END;
