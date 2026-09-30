DROP TRIGGER v4_state_result_publication_digest_r1_1 ON v4.research_state_engineering_results;
DROP TRIGGER v4_state_publication_digest_r1_1 ON v4.research_state_engineering_publications;
DROP FUNCTION v4.guard_state_publication_digest_r1_1();
DROP TRIGGER v4_state_identity_r1_1 ON v4.research_state_engineering_results;
DROP FUNCTION v4.guard_state_identity_r1_1();
ALTER TABLE v4.research_state_engineering_results
    DROP COLUMN interface_contract_id,
    DROP COLUMN canonicalization_contract_id,
    DROP COLUMN calendar_publication_id,
    DROP COLUMN calendar_lineage_id,
    DROP COLUMN calendar_manifest_digest,
    DROP COLUMN input_publication_manifest_digest,
    DROP COLUMN input_provenance,
    DROP COLUMN boundary_event,
    DROP COLUMN prior_engineering_publication_id,
    DROP COLUMN prior_row_payload_digest;
DROP TABLE v4.research_state_input_manifests;
DROP TABLE v4.research_state_field_policy_r1_1;
DROP TABLE v4.research_state_lineage_ledger;
DROP FUNCTION v4.state_digest_r1_1(jsonb);
DROP FUNCTION v4.state_canonical_r1_1(jsonb);
