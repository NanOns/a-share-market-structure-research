-- DM-01 native PG status schema preflight; SELECT-only, no scheduler start.
-- Run against the sole V4 business schema with an approved V4 Reader identity.
-- This script is SELECT-only; it neither creates nor repairs DDL.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT current_database() AS database_name, current_user AS role_name,
       'v4' AS jobs_schema,
       current_setting('server_version_num') AS server_version_num,
       current_setting('transaction_isolation') AS transaction_isolation,
       current_setting('transaction_read_only') AS transaction_read_only,
       inet_server_addr()::text AS server_address, inet_server_port() AS server_port;

WITH required(relation_name, column_name) AS (
    VALUES
        ('jobs_scheduler_policy_r1','id'), ('jobs_scheduler_policy_r1','enabled'),
        ('jobs_scheduler_policy_r1','revision'), ('jobs_scheduler_policy_r1','updated_at'),
        ('jobs_update_jobs_r1','job_id'), ('jobs_update_jobs_r1','mode'), ('jobs_update_jobs_r1','through_date'),
        ('jobs_update_jobs_r1','status'), ('jobs_update_jobs_r1','created_at'), ('jobs_update_jobs_r1','finished_at'),
        ('jobs_update_jobs_r1','idempotency_key'),
        ('jobs_scheduler_dispatch_r1','target'), ('jobs_scheduler_dispatch_r1','job_id'),
        ('jobs_scheduler_attempts_r1','target'), ('jobs_scheduler_attempts_r1','attempt_ordinal'),
        ('jobs_scheduler_attempts_r1','job_id'), ('jobs_scheduler_attempts_r1','source_revision'),
        ('jobs_scheduler_attempts_r1','reason'), ('jobs_scheduler_attempts_r1','created_at'),
        ('jobs_scheduler_rearm_r1','target'), ('jobs_scheduler_rearm_r1','revision'), ('jobs_scheduler_rearm_r1','reason'),
        ('jobs_update_job_days_r1','job_id'), ('jobs_update_job_days_r1','trade_date'), ('jobs_update_job_days_r1','state'),
        ('jobs_update_job_days_r1','attempt_count'), ('jobs_update_job_days_r1','next_retry_at'), ('jobs_update_job_days_r1','source_checks'),
        ('jobs_update_events_r1','event_id'), ('jobs_update_events_r1','job_id'), ('jobs_update_events_r1','timestamp'),
        ('jobs_update_events_r1','stage'), ('jobs_update_events_r1','event_code'), ('jobs_update_events_r1','safe_detail'),
        ('jobs_update_job_progress_r1','job_id'), ('jobs_update_job_progress_r1','trade_date'), ('jobs_update_job_progress_r1','stage'),
        ('jobs_update_job_progress_r1','stage_started_at'), ('jobs_update_job_progress_r1','last_progress_at'),
        ('jobs_update_job_progress_r1','heartbeat_at'), ('jobs_update_job_progress_r1','processed'), ('jobs_update_job_progress_r1','total'),
        ('jobs_update_job_progress_r1','unit'), ('jobs_update_job_progress_r1','recent_message'), ('jobs_update_job_progress_r1','mode'),
        ('jobs_source_probe_state_r1','target'), ('jobs_source_probe_state_r1','payload'), ('jobs_source_probe_state_r1','updated_at')
)
SELECT required.relation_name, required.column_name,
       (c.oid IS NOT NULL AND a.attnum IS NOT NULL) AS present
  FROM required
  LEFT JOIN pg_class c ON c.oid=to_regclass(format('%I.%I','v4',required.relation_name))
  LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attname=required.column_name
       AND a.attnum>0 AND NOT a.attisdropped
 ORDER BY required.relation_name,required.column_name;

SELECT required.index_name,
       EXISTS (SELECT 1 FROM pg_class i JOIN pg_namespace n ON n.oid=i.relnamespace
                WHERE n.nspname='v4' AND i.relname=required.index_name
                  AND i.relkind='i' AND i.relkind IS NOT NULL) AS present
  FROM (VALUES ('jobs_update_job_days_published_trade_date_r1'),
               ('jobs_status_time_r1'), ('jobs_events_r1')) AS required(index_name)
 ORDER BY required.index_name;

SELECT status, mode, count(*) AS job_count
  FROM v4.jobs_update_jobs_r1
 GROUP BY status,mode
 ORDER BY status,mode;

SELECT state, count(*) AS day_count,
       count(*) FILTER (WHERE next_retry_at IS NOT NULL) AS scheduled_retry_count
  FROM v4.jobs_update_job_days_r1
 GROUP BY state
 ORDER BY state;

COMMIT;
