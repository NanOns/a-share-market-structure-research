-- FOCUS_OUTCOME_SETTLEMENT_SCHEMA_V1; additive outcome retry and lifecycle audit.
CREATE TABLE IF NOT EXISTS workbench.focus_outcome_settlement_batches (
    settlement_batch_id text PRIMARY KEY,
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    as_of_trade_date date NOT NULL,
    evaluation_basis text NOT NULL CHECK
      (evaluation_basis IN ('REAL_FORWARD','HISTORICAL_RECONSTRUCTED')),
    source_identity_digest char(64) NOT NULL CHECK (source_identity_digest ~ '^[0-9a-f]{64}$'),
    calendar_digest char(64) NOT NULL CHECK (calendar_digest ~ '^[0-9a-f]{64}$'),
    normalized_artifact_sha256 char(64) NOT NULL CHECK (normalized_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    input_digest char(64) NOT NULL CHECK (input_digest ~ '^[0-9a-f]{64}$'),
    outcome_count integer NOT NULL CHECK (outcome_count >= 0),
    terminal_count integer NOT NULL CHECK (terminal_count BETWEEN 0 AND outcome_count),
    created_at_utc timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (focus_run_id,input_digest)
);

CREATE TABLE IF NOT EXISTS workbench.focus_outcome_settlement_tasks (
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    as_of_trade_date date NOT NULL,
    status text NOT NULL CHECK (status IN ('RETRY_PENDING','COMPLETE')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_error_code text,
    last_input_digest char(64) CHECK (last_input_digest IS NULL OR last_input_digest ~ '^[0-9a-f]{64}$'),
    next_retry_at_utc timestamptz,
    updated_at_utc timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (focus_run_id,as_of_trade_date),
    CHECK ((status='RETRY_PENDING') OR (last_error_code IS NULL AND next_retry_at_utc IS NULL))
);

CREATE TABLE IF NOT EXISTS workbench.focus_episode_followup_events (
    event_id text PRIMARY KEY,
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    event_type text NOT NULL CHECK (event_type IN ('FOLLOW_UP_COMPLETED','SETTLEMENT_REOPENED')),
    event_trade_date date NOT NULL,
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    settlement_batch_id text NOT NULL REFERENCES workbench.focus_outcome_settlement_batches(settlement_batch_id),
    evidence_digest char(64) NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(reason_codes)='array'),
    created_at_utc timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (episode_id,event_type,settlement_batch_id)
);

CREATE INDEX IF NOT EXISTS focus_outcome_tasks_retry_idx
  ON workbench.focus_outcome_settlement_tasks(status,next_retry_at_utc);
CREATE INDEX IF NOT EXISTS focus_followup_events_episode_idx
  ON workbench.focus_episode_followup_events(episode_id,event_trade_date DESC,created_at_utc DESC);
