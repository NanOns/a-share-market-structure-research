-- M9-01 cycle state metrics.  These nullable additions keep the original
-- sector vector and M10 common-width columns immutable while materialising
-- the M9 strong-member, high-count, retention, and diffusion contract.
ALTER TABLE sector_cycle_daily ADD COLUMN strong_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high20_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high30_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high60_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high100_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high20_valid_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high30_valid_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high60_valid_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN high100_valid_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN comparable_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN previous_strong_total BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN comparable_previous_strong BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN retained_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN entered_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN exited_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN uncomparable_count BIGINT;
ALTER TABLE sector_cycle_daily ADD COLUMN retention_rate DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN comparison_coverage DOUBLE;
ALTER TABLE sector_cycle_daily ADD COLUMN diffusion_state VARCHAR;
