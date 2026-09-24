CREATE TABLE IF NOT EXISTS workbench.publication_source_identity_migrations (
    publication_id text PRIMARY KEY REFERENCES workbench.publications(publication_id),
    source_identity_sha256 char(64) NOT NULL CHECK (source_identity_sha256 ~ '^[0-9a-f]{64}$'),
    source_bundle_id text NOT NULL,
    source_bundle_manifest_sha256 char(64) NOT NULL CHECK (source_bundle_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    target_trade_date date NOT NULL,
    contract_id text NOT NULL,
    verified_at_utc timestamptz NOT NULL,
    evidence_digest char(64) NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    verifier_id text NOT NULL,
    CHECK (length(source_bundle_id) > 0),
    CHECK (length(verifier_id) > 0)
);
