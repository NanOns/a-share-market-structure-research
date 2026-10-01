-- Allocated exclusively by unified migration allocator R3. 026 remains immutable.
DO $$ DECLARE item record; BEGIN
 FOR item IN SELECT conname FROM pg_constraint
  WHERE conrelid='v4.confirmation_candidate_facts_r1'::regclass AND contype='c'
  AND pg_get_constraintdef(oid) LIKE '%amount_A_formal_branch%'
 LOOP EXECUTE format('ALTER TABLE v4.confirmation_candidate_facts_r1 DROP CONSTRAINT %I',item.conname); END LOOP;
END $$;
ALTER TABLE v4.confirmation_candidate_facts_r1 ADD CONSTRAINT confirmation_stock_amr20_semantic_r2 CHECK ((
 (NOT(payload ? 'semantic_erratum_id') AND payload->>'amount_A_formal_branch'='DISABLED') OR
 (payload->>'semantic_erratum_id'='V4_11_STOCK_AMR20_SEMANTIC_ERRATUM_R2'
 AND payload->>'stock_amount_field_family'='STOCK_AMOUNT_VOLUME_STATE_V1'
 AND payload->>'sector_amount_A_status_affects_confirmation'='false'
 AND NOT(payload ? 'amount_A_formal_branch'))
) IS TRUE);
