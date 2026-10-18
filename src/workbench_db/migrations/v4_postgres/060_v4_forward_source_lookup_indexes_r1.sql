-- Keep source-ingress lookups selective inside the shared append-only facts
-- relation. These partial expression indexes touch only the typed source
-- families and avoid scanning unrelated Forward/Owner payloads.
CREATE INDEX IF NOT EXISTS forward_source_ingress_path_origin_sha_r1
    ON v4.forward_facts (
        workspace_namespace,
        (payload::jsonb ->> 'source_path'),
        (payload::jsonb ->> 'source_origin'),
        (payload::jsonb ->> 'source_sha256')
    )
    WHERE kind = 'historical_source_ingress';

CREATE INDEX IF NOT EXISTS forward_source_ingress_id_r1
    ON v4.forward_facts (
        workspace_namespace,
        (payload::jsonb ->> 'source_id')
    )
    WHERE kind = 'historical_source_ingress';

CREATE INDEX IF NOT EXISTS forward_source_package_identity_r1
    ON v4.forward_facts (
        workspace_namespace,
        (payload::jsonb ->> 'source_id'),
        (payload::jsonb ->> 'source_sha256')
    )
    WHERE kind = 'source_package_manifest';
