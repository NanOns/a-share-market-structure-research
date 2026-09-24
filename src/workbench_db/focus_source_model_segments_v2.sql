ALTER TABLE workbench.focus_episode_segments
    ADD COLUMN IF NOT EXISTS selection_contract_family text;

UPDATE workbench.focus_episode_segments s
SET selection_contract_family=e.selection_contract_family
FROM workbench.focus_episodes e
WHERE e.episode_id=s.episode_id AND s.selection_contract_family IS NULL;

ALTER TABLE workbench.focus_episode_segments
    ALTER COLUMN selection_contract_family SET NOT NULL;

DO $$
DECLARE item record;
BEGIN
    FOR item IN
        SELECT conname FROM pg_constraint
        WHERE conrelid='workbench.focus_episode_segments'::regclass
          AND contype='u'
          AND pg_get_constraintdef(oid) LIKE
              'UNIQUE (episode_id, segment_type, start_trade_date, source_model_contract_id, state_contract_id)%'
    LOOP
        EXECUTE format('ALTER TABLE workbench.focus_episode_segments DROP CONSTRAINT %I', item.conname);
    END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS focus_episode_segments_run_identity_uq
    ON workbench.focus_episode_segments
       (episode_id,segment_type,start_trade_date,source_model_contract_id,
        state_contract_id,focus_run_id);
