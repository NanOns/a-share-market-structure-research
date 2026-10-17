from __future__ import annotations

import pytest

from workbench_db.v4_native import workspace_namespace_identity
from workbench_db.v4_workspace_owner_mapping_r1 import (
    WorkspaceOwnerMappingError,
    resolve_workspace_owner_mapping_document,
)


def _registry(root, *, namespace="workspace-main"):
    identity = workspace_namespace_identity(root, "publication")
    return {
        "contract_id": "V4_PG_WORKSPACE_OWNER_MAPPING_REGISTRY_R1",
        "contract_version": "1.0.0",
        "status": "ACTIVE",
        "mappings": [{
            "status": "APPROVED",
            "root_identity_sha256": identity["root_identity_sha256"],
            "model_namespace_id": namespace,
            "valid_from": "2026-10-01",
            "valid_to": None,
            "authorized_by": "test-approver",
            "authorization_reference": "test-approval-reference",
            "database_identity": {
                "database": "market_research", "database_oid": 16384,
                "host": "127.0.0.1", "port": 5432,
            },
            "owner_schemas": {
                "research_priority": "v4_research_priority_aaaaaaaaaaaaaaaa",
                "operational_risk": "v4_operational_risk_aaaaaaaaaaaaaaaa",
                "sector_lifecycle": "v4_sector_lifecycle_aaaaaaaaaaaaaaaa",
            },
        }],
    }


def test_pg_contract_mapping_resolves_exact_root_namespace_and_owner_schemas(tmp_path):
    mapping = resolve_workspace_owner_mapping_document(
        root=tmp_path, trade_date="2026-10-16", selected_model_namespace_id="workspace-main",
        registry=_registry(tmp_path),
    )

    assert mapping["contract_id"] == "V4_PG_WORKSPACE_OWNER_MAPPING_R1"
    assert mapping["owner_schemas"]["research_priority"] == "v4_research_priority_aaaaaaaaaaaaaaaa"
    assert mapping["database_identity"]["database"] == "market_research"


def test_pg_contract_mapping_fails_closed_for_namespace_mismatch(tmp_path):
    with pytest.raises(WorkspaceOwnerMappingError, match="WORKSPACE_OWNER_MAPPING_NOT_AUTHORIZED"):
        resolve_workspace_owner_mapping_document(
            root=tmp_path, trade_date="2026-10-16", selected_model_namespace_id="other-workspace",
            registry=_registry(tmp_path),
        )
