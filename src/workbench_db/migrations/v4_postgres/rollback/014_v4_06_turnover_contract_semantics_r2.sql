-- Isolated rollback for an empty V4-06 R2 candidate schema only. Never run
-- against populated candidate/production data: R2 percentiles may be > 1.
ALTER TABLE v4.stock_profile_enrichments
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_pct5_r2_range_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_pct20_r2_range_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_pct60_r2_range_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_state_r2_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_turnover_alias_r2_check,
    DROP CONSTRAINT IF EXISTS stock_profile_enrichments_extension_note_r2_check,
    DROP COLUMN IF EXISTS supplemental_extension_note;

ALTER TABLE v4.stock_profile_enrichments
    ADD CONSTRAINT stock_profile_enrichments_turnover_pct5_check
        CHECK (turnover_pct5 IS NULL OR (turnover_pct5 >= 0 AND turnover_pct5 <= 1)),
    ADD CONSTRAINT stock_profile_enrichments_turnover_pct20_check
        CHECK (turnover_pct20 IS NULL OR (turnover_pct20 >= 0 AND turnover_pct20 <= 1)),
    ADD CONSTRAINT stock_profile_enrichments_turnover_pct60_check
        CHECK (turnover_pct60 IS NULL OR (turnover_pct60 >= 0 AND turnover_pct60 <= 1));
