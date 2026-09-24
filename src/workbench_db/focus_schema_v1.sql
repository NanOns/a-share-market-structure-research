-- FOCUS_PG_SCHEMA_V1; PostgreSQL only. Installed transactionally by
-- scripts/apply_focus_pg_schema_v1.py after workbench migration acceptance.
CREATE TABLE IF NOT EXISTS workbench.focus_runs (
    focus_run_id text PRIMARY KEY,
    trade_date date NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    publication_id text NOT NULL REFERENCES workbench.publications(publication_id),
    source_authority_contract_id text NOT NULL,
    source_family_set jsonb NOT NULL,
    family_capabilities jsonb NOT NULL,
    source_identity_digest char(64) NOT NULL,
    calendar_digest char(64) NOT NULL,
    observation_input_digest char(64) NOT NULL,
    state_contract_id text NOT NULL,
    parameter_set_id text NOT NULL,
    price_basis text NOT NULL,
    dependency_lock_hash char(64) NOT NULL,
    evaluation_basis text NOT NULL CHECK (evaluation_basis IN ('REAL_FORWARD','HISTORICAL_RECONSTRUCTED')),
    core_publication_status text NOT NULL CHECK (core_publication_status IN ('BUILDING','READY','ACTIVATED','FAILED')),
    outcome_settlement_status text NOT NULL DEFAULT 'PENDING'
      CHECK (outcome_settlement_status IN ('PENDING','COMPLETE','DEGRADED')),
    created_at_utc timestamptz NOT NULL DEFAULT now(),
    activated_at_utc timestamptz,
    UNIQUE (trade_date, source_authority_contract_id, revision),
    CHECK ((core_publication_status = 'ACTIVATED') = (activated_at_utc IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS workbench.focus_daily_items (
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    source_family text NOT NULL,
    entity_type text NOT NULL CHECK (entity_type IN ('STOCK','SECTOR')),
    entity_id text NOT NULL,
    selection_contract_family text NOT NULL,
    source_item_key text NOT NULL,
    source_item_digest char(64) NOT NULL,
    source_contract_id text NOT NULL,
    source_membership_state text NOT NULL CHECK (source_membership_state IN ('CURRENT','EARLY','CANDIDATE','INDIVIDUAL')),
    source_focus_class text,
    source_rank integer,
    source_quality text NOT NULL,
    source_facts jsonb NOT NULL,
    PRIMARY KEY (focus_run_id,source_family,entity_type,entity_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_episodes (
    episode_id text PRIMARY KEY,
    source_family text NOT NULL,
    entity_type text NOT NULL CHECK (entity_type IN ('STOCK','SECTOR')),
    entity_id text NOT NULL,
    selection_contract_family text NOT NULL,
    first_trade_date date NOT NULL,
    first_focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    parent_episode_id text REFERENCES workbench.focus_episodes(episode_id),
    UNIQUE (source_family,entity_type,entity_id,first_trade_date,selection_contract_family),
    CHECK (episode_id IS DISTINCT FROM parent_episode_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_episode_segments (
    segment_id text PRIMARY KEY,
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    segment_type text NOT NULL CHECK (segment_type IN ('SOURCE_MODEL','INTERPRETATION')),
    start_trade_date date NOT NULL,
    source_model_contract_id text NOT NULL,
    state_contract_id text NOT NULL,
    parameter_set_id text NOT NULL,
    boundary_reason text NOT NULL,
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    UNIQUE (episode_id,segment_type,start_trade_date,source_model_contract_id,state_contract_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_episode_transitions (
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    source_revision integer NOT NULL CHECK (source_revision > 0),
    transition_trade_date date NOT NULL,
    effective_trade_date date NOT NULL,
    confirmation_trade_date date NOT NULL,
    transition_type text NOT NULL,
    from_membership text NOT NULL,
    to_membership text NOT NULL,
    reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (episode_id,focus_run_id,transition_type),
    CHECK (transition_trade_date=effective_trade_date AND transition_trade_date=confirmation_trade_date)
);

CREATE TABLE IF NOT EXISTS workbench.focus_episode_anchors (
    anchor_id text PRIMARY KEY,
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    anchor_type text NOT NULL CHECK (anchor_type IN
      ('FIRST_FOCUS','CURRENT_UPGRADE','EXIT_EFFECTIVE','INVALIDATION','FIRST_SUPPORTED','MILESTONE')),
    trade_date date NOT NULL,
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    source_revision integer NOT NULL CHECK (source_revision > 0),
    reference_price numeric(18,4),
    price_basis text NOT NULL,
    quality_status text NOT NULL,
    source_fact_digest char(64) NOT NULL,
    UNIQUE (episode_id,anchor_type,focus_run_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_episode_observations (
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    trade_date date NOT NULL,
    source_revision integer NOT NULL CHECK (source_revision > 0),
    evaluation_mode text NOT NULL CHECK (evaluation_mode IN ('AS_RECORDED','REINTERPRETED')),
    state_contract_id text NOT NULL,
    source_membership_state text NOT NULL,
    membership_phase text NOT NULL,
    validity_state text NOT NULL CHECK (validity_state IN ('VALID','INVALIDATED','UNKNOWN')),
    followup_state text NOT NULL,
    current_path_state text NOT NULL,
    lifetime_path_tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    continuity_quality text NOT NULL,
    comparison_gap_sessions integer NOT NULL DEFAULT 0 CHECK (comparison_gap_sessions >= 0),
    entry_primary_sector_id text,
    current_primary_sector_id text,
    first_supported_anchor_id text REFERENCES workbench.focus_episode_anchors(anchor_id),
    close_price numeric(18,4),
    return_since_first numeric(24,12),
    drawdown_from_peak numeric(24,12),
    adjustment_source_hash char(64),
    quality_status text NOT NULL,
    fact_digest char(64) NOT NULL,
    facts jsonb NOT NULL,
    PRIMARY KEY (episode_id,trade_date,source_revision,evaluation_mode,state_contract_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_episode_outcomes (
    anchor_id text NOT NULL REFERENCES workbench.focus_episode_anchors(anchor_id),
    horizon integer NOT NULL CHECK (horizon IN (1,3,5,10,20)),
    target_revision integer NOT NULL CHECK (target_revision > 0),
    target_trade_date date NOT NULL,
    status text NOT NULL CHECK (status IN
      ('PENDING','OBSERVED','DATA_GAP','SUSPENDED','DELISTED','SOURCE_REVISED')),
    evaluation_basis text NOT NULL CHECK (evaluation_basis IN ('REAL_FORWARD','HISTORICAL_RECONSTRUCTED')),
    forward_return numeric(24,12),
    mfe numeric(24,12),
    mae numeric(24,12),
    mdd numeric(24,12),
    input_digest char(64) NOT NULL,
    reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    evidence jsonb NOT NULL,
    observed_at_utc timestamptz,
    PRIMARY KEY (anchor_id,horizon,target_revision),
    CHECK (status='OBSERVED' OR (forward_return IS NULL AND mfe IS NULL AND mae IS NULL AND mdd IS NULL))
);

CREATE TABLE IF NOT EXISTS workbench.focus_outcome_heads (
    anchor_id text NOT NULL,
    horizon integer NOT NULL,
    accepted_target_revision integer NOT NULL,
    activated_at_utc timestamptz NOT NULL,
    PRIMARY KEY (anchor_id,horizon),
    FOREIGN KEY (anchor_id,horizon,accepted_target_revision)
      REFERENCES workbench.focus_episode_outcomes(anchor_id,horizon,target_revision)
);

CREATE TABLE IF NOT EXISTS workbench.focus_stock_sector_links (
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    security_id text NOT NULL,
    sector_id text NOT NULL,
    relation_type text NOT NULL,
    support_status text NOT NULL,
    loo_status text NOT NULL,
    is_primary boolean NOT NULL,
    source_fact_digest char(64) NOT NULL,
    evidence jsonb NOT NULL,
    PRIMARY KEY (focus_run_id,security_id,sector_id,relation_type)
);

CREATE TABLE IF NOT EXISTS workbench.focus_current_projection (
    source_family text NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    active_episode_id text REFERENCES workbench.focus_episodes(episode_id),
    last_episode_id text REFERENCES workbench.focus_episodes(episode_id),
    latest_trade_date date NOT NULL,
    latest_focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    source_membership_state text NOT NULL,
    membership_phase text NOT NULL,
    validity_state text NOT NULL,
    followup_state text NOT NULL,
    current_path_state text NOT NULL,
    projection_digest char(64) NOT NULL,
    PRIMARY KEY (source_family,entity_type,entity_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_trade_date_heads (
    trade_date date NOT NULL,
    source_authority_contract_id text NOT NULL,
    accepted_focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    accepted_revision integer NOT NULL,
    predecessor_focus_run_id text REFERENCES workbench.focus_runs(focus_run_id),
    lineage_state text NOT NULL CHECK (lineage_state IN ('VALID','REPLAY_REQUIRED')),
    activated_at_utc timestamptz NOT NULL,
    PRIMARY KEY (trade_date,source_authority_contract_id)
);

CREATE TABLE IF NOT EXISTS workbench.focus_state_evaluations (
    state_evaluation_id text PRIMARY KEY,
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    trade_date date NOT NULL,
    source_revision integer NOT NULL,
    state_contract_id text NOT NULL,
    parameter_set_id text NOT NULL,
    evaluation_mode text NOT NULL CHECK (evaluation_mode IN ('AS_RECORDED','REINTERPRETED')),
    validity_state text NOT NULL,
    current_path_state text NOT NULL,
    quality_status text NOT NULL,
    evidence_digest char(64) NOT NULL,
    created_at_utc timestamptz NOT NULL DEFAULT now(),
    UNIQUE (episode_id,trade_date,source_revision,state_contract_id,evaluation_mode)
);

CREATE TABLE IF NOT EXISTS workbench.focus_state_evaluation_facts (
    state_evaluation_id text NOT NULL REFERENCES workbench.focus_state_evaluations(state_evaluation_id),
    predicate_id text NOT NULL,
    operand_mode text NOT NULL,
    result text NOT NULL CHECK (result IN ('TRUE','FALSE','UNKNOWN','NOT_APPLICABLE')),
    actual jsonb,
    expected jsonb,
    reason_code text,
    evidence jsonb NOT NULL,
    PRIMARY KEY (state_evaluation_id,predicate_id)
);

CREATE INDEX IF NOT EXISTS focus_daily_items_lookup_idx ON workbench.focus_daily_items(focus_run_id,source_family,source_rank);
CREATE INDEX IF NOT EXISTS focus_episode_entity_idx ON workbench.focus_episodes(source_family,entity_type,entity_id,first_trade_date DESC);
CREATE INDEX IF NOT EXISTS focus_observation_date_idx ON workbench.focus_episode_observations(trade_date,episode_id);
CREATE INDEX IF NOT EXISTS focus_outcomes_due_idx ON workbench.focus_episode_outcomes(status,target_trade_date);
CREATE INDEX IF NOT EXISTS focus_projection_state_idx ON workbench.focus_current_projection(followup_state,latest_trade_date DESC);
