-- R21-R4 contract registry catalog preflight; SELECT-only, no migration.
-- Execute with the approved V4 reader identity after reviewing the returned
-- database identity and privilege row. This does not inspect contract bytes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT current_database() AS database_name,
       current_user AS role_name,
       current_setting('server_version_num') AS server_version_num,
       current_setting('transaction_isolation') AS transaction_isolation,
       current_setting('transaction_read_only') AS transaction_read_only,
       inet_server_addr()::text AS server_address,
       inet_server_port() AS server_port;

WITH required(relation_name, column_name) AS (
    VALUES
        ('v4.model_namespaces', 'namespace_id'),
        ('v4.model_namespaces', 'namespace'),
        ('v4.publications', 'publication_id'),
        ('v4.publications', 'revision_no'),
        ('v4.publications', 'trade_date'),
        ('v4.publications', 'model_namespace_id'),
        ('v4.publications', 'status'),
        ('v4.publications', 'accepted_at')
)
SELECT required.relation_name, required.column_name,
       (c.oid IS NOT NULL AND a.attnum IS NOT NULL) AS present
  FROM required
  LEFT JOIN pg_class c ON c.oid = to_regclass(required.relation_name)
  LEFT JOIN pg_attribute a ON a.attrelid = c.oid
       AND a.attname = required.column_name
       AND a.attnum > 0 AND NOT a.attisdropped
 ORDER BY required.relation_name, required.column_name;

SELECT to_regprocedure('sha256(bytea)') IS NOT NULL AS builtin_sha256_available,
       to_regclass('v4.contract_versions') IS NOT NULL AS contract_versions_exists,
       to_regclass('v4.contract_approval_events') IS NOT NULL AS approval_events_exists,
       EXISTS (SELECT 1 FROM pg_attribute
                WHERE attrelid = to_regclass('v4.publications')
                  AND attname = 'contract_bindings'
                  AND attnum > 0 AND NOT attisdropped) AS publication_bindings_column_exists,
       EXISTS (SELECT 1 FROM pg_trigger
                WHERE tgrelid = to_regclass('v4.publications')
                  AND tgname = 'publication_contract_bindings_guard'
                  AND NOT tgisinternal) AS publication_binding_guard_exists;

SELECT has_schema_privilege(current_user, 'v4', 'USAGE') AS schema_usage,
       has_schema_privilege(current_user, 'v4', 'CREATE') AS schema_create,
       has_table_privilege(current_user, 'v4.publications', 'SELECT') AS publications_select,
       has_table_privilege(current_user, 'v4.publications', 'INSERT') AS publications_insert,
       has_table_privilege(current_user, 'v4.publications', 'UPDATE') AS publications_update,
       has_table_privilege(current_user, 'v4.publications', 'DELETE') AS publications_delete,
       has_table_privilege(current_user, to_regclass('v4.contract_versions'), 'SELECT') AS versions_select,
       has_table_privilege(current_user, to_regclass('v4.contract_approval_events'), 'SELECT') AS approval_events_select;

SELECT status,
       count(*) AS publication_count,
       count(*) FILTER (WHERE accepted_at IS NOT NULL) AS accepted_at_count
  FROM v4.publications
 GROUP BY status
 ORDER BY status;

COMMIT;
