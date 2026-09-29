-- Isolated rollback: remove only the empty V4-07 candidate table.
-- Never apply against a database containing V4-07 stage rows.
DROP TABLE IF EXISTS v4.base_seed_results;