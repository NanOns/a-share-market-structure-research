"""FEP dataset persistence is disabled until fixed v4 tables are migrated."""


def persist_dataset(pg, dataset_id, scope_id, feature_contract_id, policy_contract_id,
                    dataset_cutoff, created_at, assembled):
    raise RuntimeError('V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED')
