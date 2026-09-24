-- FOCUS_EPISODE_BASKET_V1; additive, immutable entry basket revisions.
CREATE TABLE IF NOT EXISTS workbench.focus_episode_baskets (
    episode_id text NOT NULL REFERENCES workbench.focus_episodes(episode_id),
    focus_run_id text NOT NULL REFERENCES workbench.focus_runs(focus_run_id),
    publication_id text NOT NULL REFERENCES workbench.publications(publication_id),
    source_kind text NOT NULL CHECK (source_kind IN
      ('BOUND_RELATION_REVISION','MEMBERSHIP_SNAPSHOT')),
    source_identity text NOT NULL CHECK (length(source_identity)>0),
    member_ids jsonb NOT NULL CHECK (jsonb_typeof(member_ids)='array'),
    member_count integer NOT NULL CHECK (member_count>0),
    basket_digest char(64) NOT NULL CHECK (basket_digest ~ '^[0-9a-f]{64}$'),
    created_at_utc timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (episode_id,focus_run_id),
    CHECK (jsonb_array_length(member_ids)=member_count)
);
CREATE INDEX IF NOT EXISTS focus_episode_baskets_run_idx
  ON workbench.focus_episode_baskets(focus_run_id,episode_id);
