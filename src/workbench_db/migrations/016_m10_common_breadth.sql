-- M10 B uses width measured on the same common-valid member set for both
-- dates.  The original breadth_ret1 remains the all-current-members
-- descriptive statistic; these fields are the versioned M10 comparison
-- inputs and retain their valid counts for auditability.
ALTER TABLE sector_cycle_daily ADD COLUMN breadth_ret1_common DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN breadth_ret1_common_valid_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN breadth_ret1_common_change_1d DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN breadth_ret1_common_change_1d_valid_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN breadth_ret1_common_change_3d DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN breadth_ret1_common_change_3d_valid_count BIGINT;
