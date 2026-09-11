-- M10-amount-A formal common-member aggregate.
-- The legacy amount_vs_prior20/current_amount_vs_prior20 columns are retained
-- as immutable compatibility fields.  These nullable columns are the explicit
-- formal A and its evidence; old slices remain LEGACY_PROXY.
ALTER TABLE sector_cycle_daily ADD COLUMN member_amount_ratio_median_vs_prior20 DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN sector_amount_vs_prior20 DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN sector_amount_comparable_sum DECIMAL(28, 2);
ALTER TABLE sector_cycle_daily ADD COLUMN sector_amount_prior20_mean DECIMAL(28, 2);
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparable_member_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_target_member_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparable_coverage DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_window_coverage DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_window_target_member_max BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_target_denominator_source VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_window_denominator_source VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_basis VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_quality_codes JSON;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_excluded_member_ids JSON;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_member_set_hash VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_membership_snapshot_id VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_window_start DATE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_window_end DATE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_contract_id VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN sector_amount_ratio_delta_3sessions_common DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_date DATE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_current_a DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_prior_a DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_current_sum DECIMAL(28, 2);
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_current_prior20_mean DECIMAL(28, 2);
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_prior_sum DECIMAL(28, 2);
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_prior_prior20_mean DECIMAL(28, 2);
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_member_set_hash VARCHAR;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_current_coverage DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_prior_coverage DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_window_coverage DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_window_start DATE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_window_end DATE;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_quality_codes JSON;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_excluded_member_ids JSON;
ALTER TABLE sector_cycle_daily ADD COLUMN amount_comparison_evidence JSON;

ALTER TABLE mainline_daily ADD COLUMN current_sector_amount_vs_prior20 DOUBLE;
ALTER TABLE mainline_daily ADD COLUMN sector_amount_ratio_delta_3sessions_common DOUBLE;
ALTER TABLE mainline_daily ADD COLUMN sector_amount_quality_codes JSON;
ALTER TABLE mainline_daily ADD COLUMN sector_amount_basis VARCHAR;
ALTER TABLE mainline_daily ADD COLUMN sector_amount_membership_snapshot_id VARCHAR;
ALTER TABLE mainline_daily ADD COLUMN sector_amount_comparison_evidence JSON;
ALTER TABLE mainline_daily ADD COLUMN sector_amount_contract_id VARCHAR;
