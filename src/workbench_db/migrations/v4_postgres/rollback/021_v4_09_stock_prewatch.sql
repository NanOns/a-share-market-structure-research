DROP TABLE v4.stock_prewatch_results;
DROP TABLE v4.stock_prewatch_publications;
DROP FUNCTION v4.guard_stock_prewatch_binding();
DELETE FROM v4_meta.schema_migrations WHERE version='V4_09_STOCK_PREWATCH_V1';
