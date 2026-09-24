CREATE TABLE IF NOT EXISTS workbench.focus_episode_frozen_fact_revisions (
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    source_trade_date date NOT NULL,
    source_revision integer NOT NULL CHECK (source_revision > 0),
    fact_key text NOT NULL CHECK (fact_key IN
        ('frozen_phh20','frozen_pullback_invalid_low','frozen_trend_key_low','reclaimed_ma_kind')),
    fact_value text,
    fact_type text NOT NULL CHECK (fact_type IN ('PRICE','MA_IDENTITY')),
    source_fact_digest char(64) NOT NULL,
    frozen_at_trade_date date NOT NULL,
    contract_id text NOT NULL,
    reason text NOT NULL CHECK (reason IN ('SOURCE_OPERAND','SOURCE_OPERAND_UNAVAILABLE')),
    created_at_utc timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (episode_id,source_trade_date,source_revision,fact_key),
    CHECK ((fact_value IS NULL) = (reason = 'SOURCE_OPERAND_UNAVAILABLE'))
);

CREATE INDEX IF NOT EXISTS focus_frozen_fact_revision_lookup_idx
    ON workbench.focus_episode_frozen_fact_revisions
       (episode_id,source_trade_date,source_revision);
