-- DM-01 native PG status schema preflight; SELECT-only, no scheduler start.
-- Run in the target workspace with its configured schema on search_path and
-- an approved V4 Reader identity. This script neither creates nor repairs DDL.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT current_database() AS database_name, current_user AS role_name,
       current_schema() AS jobs_schema,
       current_setting('server_version_num') AS server_version_num,
       current_setting('transaction_isolation') AS transaction_isolation,
       current_setting('transaction_read_only') AS transaction_read_only,
       inet_server_addr()::text AS server_address, inet_server_port() AS server_port;

WITH required(relation_name, column_name) AS (
    VALUES
        ('scheduler_policy','id'), ('scheduler_policy','enabled'),
        ('scheduler_policy','revision'), ('scheduler_policy','updated_at'),
        ('update_jobs','job_id'), ('update_jobs','mode'), ('update_jobs','through_date'),
        ('update_jobs','status'), ('update_jobs','created_at'), ('update_jobs','finished_at'),
        ('update_jobs','idempotency_key'),
        ('scheduler_dispatch','target'), ('scheduler_dispatch','job_id'),
        ('scheduler_attempts','target'), ('scheduler_attempts','attempt_ordinal'),
        ('scheduler_attempts','job_id'), ('scheduler_attempts','source_revision'),
        ('scheduler_attempts','reason'), ('scheduler_attempts','created_at'),
        ('scheduler_rearm','target'), ('scheduler_rearm','revision'), ('scheduler_rearm','reason'),
        ('update_job_days','job_id'), ('update_job_days','trade_date'), ('update_job_days','state'),
        ('update_job_days','attempt_count'), ('update_job_days','next_retry_at'), ('update_job_days','source_checks'),
        ('update_events','event_id'), ('update_events','job_id'), ('update_events','timestamp'),
        ('update_events','stage'), ('update_events','event_code'), ('update_events','safe_detail'),
        ('update_job_progress','job_id'), ('update_job_progress','trade_date'), ('update_job_progress','stage'),
        ('update_job_progress','stage_started_at'), ('update_job_progress','last_progress_at'),
        ('update_job_progress','heartbeat_at'), ('update_job_progress','processed'), ('update_job_progress','total'),
        ('update_job_progress','unit'), ('update_job_progress','recent_message'), ('update_job_progress','mode'),
        ('source_probe_state','target'), ('source_probe_state','payload'), ('source_probe_state','updated_at')
)
SELECT required.relation_name, required.column_name,
       (c.oid IS NOT NULL AND a.attnum IS NOT NULL) AS present
  FROM required
  LEFT JOIN pg_class c ON c.oid=to_regclass(format('%I.%I',current_schema(),required.relation_name))
  LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attname=required.column_name
       AND a.attnum>0 AND NOT a.attisdropped
 ORDER BY required.relation_name,required.column_name;

SELECT required.index_name,
       EXISTS (SELECT 1 FROM pg_class i JOIN pg_namespace n ON n.oid=i.relnamespace
                WHERE n.nspname=current_schema() AND i.relname=required.index_name
                  AND i.relkind='i' AND i.relkind IS NOT NULL) AS present
  FROM (VALUES ('update_job_days_published_trade_date'),
               ('job_status_time'), ('job_events')) AS required(index_name)
 ORDER BY required.index_name;

SELECT status, mode, count(*) AS job_count
  FROM update_jobs
 GROUP BY status,mode
 ORDER BY status,mode;

SELECT state, count(*) AS day_count,
       count(*) FILTER (WHERE next_retry_at IS NOT NULL) AS scheduled_retry_count
  FROM update_job_days
 GROUP BY state
 ORDER BY state;

COMMIT;
