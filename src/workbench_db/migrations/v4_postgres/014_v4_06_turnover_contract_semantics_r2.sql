-- V4-06 R2 semantics repair. Migration 013 is retained unchanged so R1 remains
-- replayable. This migration touches supplemental sidecars only; Core tables
-- and accepted publication rows are not updated.
ALTER TABLE v4.stock_profile_enrichments
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_pct5_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_pct20_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_pct60_check;

ALTER TABLE v4.stock_profile_enrichments
    ADD CONSTRAINT stock_profile_enrichments_turnover_pct5_r2_range_check
        CHECK (turnover_pct5 IS NULL OR (turnover_pct5 >= 0 AND turnover_pct5 <= 100)),
    ADD CONSTRAINT stock_profile_enrichments_turnover_pct20_r2_range_check
        CHECK (turnover_pct20 IS NULL OR (turnover_pct20 >= 0 AND turnover_pct20 <= 100)),
    ADD CONSTRAINT stock_profile_enrichments_turnover_pct60_r2_range_check
        CHECK (turnover_pct60 IS NULL OR (turnover_pct60 >= 0 AND turnover_pct60 <= 100)),
    ADD CONSTRAINT stock_profile_enrichments_turnover_state_r2_check
        CHECK (turnover_state IN ('LOW','NORMAL','ELEVATED','HIGH','EXTREME','PENDING','UNAVAILABLE','UNKNOWN_DATA')) NOT VALID,
    ADD CONSTRAINT stock_profile_enrichments_turnover_alias_r2_check
        CHECK (turnover_context = turnover_state) NOT VALID,
    ADD COLUMN supplemental_extension_note jsonb,
    ADD CONSTRAINT stock_profile_enrichments_extension_note_r2_check
        CHECK (
            supplemental_extension_note IS NULL OR (
                COALESCE(
                jsonb_typeof(supplemental_extension_note) = 'object'
                AND supplemental_extension_note->>'contract_id' = 'SUPPLEMENTAL_EXTENSION_NOTE_V1'
                AND supplemental_extension_note->>'contract_version' = '1.0.0'
                AND supplemental_extension_note->>'source_revision_id' = source_revision_id
                AND supplemental_extension_note->>'source_digest' = source_digest
                AND supplemental_extension_note->>'state' IN ('AVAILABLE','PENDING','UNAVAILABLE','UNKNOWN_DATA')
                AND supplemental_extension_note->'supplemental_observation'->>'turnover_state' = turnover_state,
                FALSE
                )
            )
        ) NOT VALID;

COMMENT ON COLUMN v4.stock_profile_enrichments.supplemental_extension_note IS
    'SUPPLEMENTAL_EXTENSION_NOTE_V1 side-by-side annotation; never changes Core risk or eligibility.';
