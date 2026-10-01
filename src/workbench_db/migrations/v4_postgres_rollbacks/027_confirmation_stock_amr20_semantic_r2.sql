ALTER TABLE v4.confirmation_candidate_facts_r1 DROP CONSTRAINT confirmation_stock_amr20_semantic_r2;
-- Retain historical R2 rows; future R1 writes regain the old guard.
ALTER TABLE v4.confirmation_candidate_facts_r1 ADD CONSTRAINT confirmation_sector_disabled_legacy_r1
 CHECK((payload->>'amount_A_formal_branch'='DISABLED') IS TRUE) NOT VALID;
