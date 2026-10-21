-- R8 Batch 08: separate development source verification from historical PIT
-- and bind D0's actual computation/publication clocks and full input closure.
ALTER TABLE v4_r8d0seal_batch07_r1.publications
 ADD COLUMN IF NOT EXISTS dev_asof_source_verified boolean NOT NULL DEFAULT false,
 ADD COLUMN IF NOT EXISTS source_snapshot_cutoff_at timestamptz,
 ADD COLUMN IF NOT EXISTS code_parameters_frozen_at timestamptz,
 ADD COLUMN IF NOT EXISTS d0_computed_at timestamptz,
 ADD COLUMN IF NOT EXISTS d0_published_at timestamptz,
 ADD COLUMN IF NOT EXISTS d0_usable_at timestamptz,
 ADD COLUMN IF NOT EXISTS input_closure_fingerprint text,
 ADD COLUMN IF NOT EXISTS full_closure_fingerprint text,
 ADD COLUMN IF NOT EXISTS source_freeze_sha256 text;

ALTER TABLE v4_r8d0seal_batch07_r1.publications
 DROP CONSTRAINT IF EXISTS d0_publication_status_check,
 DROP CONSTRAINT IF EXISTS d0_truthfulness_check,
 DROP CONSTRAINT IF EXISTS d0_time_chain_order_check;
ALTER TABLE v4_r8d0seal_batch07_r1.publications
 ADD CONSTRAINT d0_publication_status_check CHECK(publication_status IN
   ('DEV_RECONSTRUCTED_NON_PIT','DEV_SOURCE_VERIFIED','DEV_ASOF_SOURCE_VERIFIED')),
 ADD CONSTRAINT d0_truthfulness_check CHECK(
   (publication_status='DEV_RECONSTRUCTED_NON_PIT' AND NOT as_recorded AND NOT pit_eligible AND NOT dev_asof_source_verified)
   OR (publication_status='DEV_SOURCE_VERIFIED' AND as_recorded AND pit_eligible AND NOT dev_asof_source_verified)
   OR (publication_status='DEV_ASOF_SOURCE_VERIFIED' AND NOT as_recorded AND NOT pit_eligible AND dev_asof_source_verified)),
 ADD CONSTRAINT d0_time_chain_order_check CHECK(
   (source_snapshot_cutoff_at IS NULL OR source_snapshot_cutoff_at=knowledge_cutoff_at)
   AND (d0_published_at IS NULL OR d0_computed_at IS NOT NULL AND d0_published_at>=d0_computed_at)
   AND (d0_usable_at IS NULL OR d0_published_at IS NOT NULL AND d0_usable_at>=d0_published_at));
CREATE INDEX IF NOT EXISTS d0_seal_input_closure_idx
 ON v4_r8d0seal_batch07_r1.publications(trade_date,candidate_token,input_closure_fingerprint);

ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources
 ADD COLUMN IF NOT EXISTS dev_asof_source_verified boolean NOT NULL DEFAULT false;
ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources
 DROP CONSTRAINT IF EXISTS d0_consumed_truthfulness_check;
ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources
 ADD CONSTRAINT d0_consumed_truthfulness_check CHECK(
   (NOT as_recorded AND NOT pit_eligible) OR
   (as_recorded AND pit_eligible AND source_available_before_cutoff AND
    evidence_class NOT IN ('RECONSTRUCTED_NON_PIT','CAPTURED_AFTER_CLOSE_NON_PIT')));
