CREATE TABLE IF NOT EXISTS workbench.focus_episode_frozen_facts (
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    fact_key text NOT NULL CHECK (fact_key IN
        ('frozen_phh20','frozen_pullback_invalid_low','frozen_trend_key_low','reclaimed_ma_kind')),
    fact_value text,
    fact_type text NOT NULL CHECK (fact_type IN ('PRICE','MA_IDENTITY')),
    source_fact_digest char(64) NOT NULL,
    frozen_at_trade_date date NOT NULL,
    contract_id text NOT NULL,
    reason text NOT NULL CHECK (reason IN ('SOURCE_OPERAND','SOURCE_OPERAND_UNAVAILABLE')),
    PRIMARY KEY (episode_id,fact_key),
    CHECK ((fact_value IS NULL) = (reason = 'SOURCE_OPERAND_UNAVAILABLE'))
);
