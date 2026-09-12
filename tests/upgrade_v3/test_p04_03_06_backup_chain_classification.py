from workbench_ops.backup import BackupService


def test_chain_classification_is_conservative_and_non_destructive():
    audit = {
        "contract_version": "v3-p04-03-backup-chain-audit-v1.0",
        "records": [
            {"backup_id": "complete", "chain_status": "PASS"},
            {"backup_id": "missing-db", "chain_status": "INCOMPLETE", "database_status": "MISSING", "manifest_status": "PASS", "object_status": "PASS"},
        ],
        "orphan_physical_database_files": ["orphan.duckdb"],
        "orphan_physical_manifest_files": ["orphan.manifest.json"],
        "orphan_physical_object_dirs": ["orphan.objects"],
    }

    result = BackupService.classify_catalog_physical_chain(audit)

    assert result["automatic_action"] == "NONE"
    assert result["deletion_allowed"] is False
    assert result["counts"] == {
        "MANUAL_RECOVERY_VALIDATION_CANDIDATE": 1,
        "PROTECTED_EVIDENCE": 1,
        "USER_DECISION_REQUIRED": 2,
    }
