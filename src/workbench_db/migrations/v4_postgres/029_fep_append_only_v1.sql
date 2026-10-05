CREATE FUNCTION fep.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'FEP_APPEND_ONLY'; END $$;
-- Explicit guards for this version; every future fact table migration must
-- create its own guard and be checked against the registry. No automatic inheritance.
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.contracts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.scopes FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.field_registry FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.field_scope FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.targets FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.observations FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.observation_revisions FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.snapshots FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.feature_values FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.label_source_bindings FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.label_revisions FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.datasets FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_eligibility_ledger FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_fold_cutoffs FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_fold_label_selection FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_rows FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.training_runs FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.models FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.model_sets FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.model_set_members FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.permission_keys FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.activations FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.deployment_change_receipts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.prediction_slots FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.slot_model_bindings FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.prediction_runs FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.predictions FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.slot_receipts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.acceptance_receipts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.reports FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.priority_projection FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.priority_projection_grants FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
