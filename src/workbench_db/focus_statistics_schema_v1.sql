-- FOCUS_STATISTICS_MATERIALIZATION_V1; immutable grouped statistics batches.
CREATE TABLE IF NOT EXISTS workbench.focus_statistics_batches (
    statistics_batch_id text PRIMARY KEY,
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    as_of_trade_date date NOT NULL,
    statistics_contract_id text NOT NULL,
    input_digest char(64) NOT NULL CHECK (input_digest ~ '^[0-9a-f]{64}$'),
    group_count integer NOT NULL CHECK (group_count >= 0),
    outcome_count integer NOT NULL CHECK (outcome_count >= 0),
    created_at_utc timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (focus_run_id,statistics_contract_id,input_digest),
    UNIQUE (statistics_batch_id,focus_run_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_statistics_rows (
    statistics_batch_id text NOT NULL REFERENCES workbench.focus_statistics_batches(statistics_batch_id),
    source_family text NOT NULL,
    entity_type text NOT NULL CHECK (entity_type IN ('STOCK','SECTOR')),
    selection_contract_family text NOT NULL,
    source_model_contract_id text NOT NULL,
    state_contract_id text NOT NULL,
    anchor_type text NOT NULL,
    horizon integer NOT NULL CHECK (horizon IN (1,3,5,10,20)),
    evaluation_basis text NOT NULL CHECK (evaluation_basis IN ('REAL_FORWARD','HISTORICAL_RECONSTRUCTED')),
    price_basis text NOT NULL,
    sample_count integer NOT NULL CHECK (sample_count >= 0),
    signal_date_count integer NOT NULL CHECK (signal_date_count >= 0),
    incomplete_count integer NOT NULL CHECK (incomplete_count >= 0),
    gate_status text NOT NULL CHECK (gate_status IN ('OPEN','INSUFFICIENT_SAMPLES','READY')),
    p25_return numeric(24,12),
    median_return numeric(24,12),
    p75_return numeric(24,12),
    max_mfe numeric(24,12),
    worst_mdd numeric(24,12),
    PRIMARY KEY (statistics_batch_id,source_family,entity_type,selection_contract_family,
                 source_model_contract_id,state_contract_id,anchor_type,horizon,evaluation_basis,price_basis),
    CHECK ((gate_status='READY' AND sample_count >= 30 AND signal_date_count >= 5
            AND p25_return IS NOT NULL AND median_return IS NOT NULL AND p75_return IS NOT NULL)
        OR (gate_status<>'READY' AND p25_return IS NULL AND median_return IS NULL
            AND p75_return IS NULL AND max_mfe IS NULL AND worst_mdd IS NULL))
);

CREATE TABLE IF NOT EXISTS workbench.focus_statistics_heads (
    focus_run_id text PRIMARY KEY REFERENCES workbench.focus_runs(focus_run_id),
    statistics_batch_id text NOT NULL,
    activated_at_utc timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (statistics_batch_id,focus_run_id)
      REFERENCES workbench.focus_statistics_batches(statistics_batch_id,focus_run_id)
);

CREATE INDEX IF NOT EXISTS focus_statistics_rows_lookup_idx
  ON workbench.focus_statistics_rows(statistics_batch_id,source_family,entity_type,horizon);
