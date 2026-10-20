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
                "research_priority": "v4",
                "operational_risk": "v4",
                "sector_lifecycle": "v4",
            },
        }],
    }


def test_pg_contract_mapping_resolves_exact_root_namespace_and_owner_schemas(tmp_path):
    mapping = resolve_workspace_owner_mapping_document(
        root=tmp_path, trade_date="2026-10-16", selected_model_namespace_id="workspace-main",
        registry=_registry(tmp_path),
    )

    assert mapping["contract_id"] == "V4_PG_WORKSPACE_OWNER_MAPPING_R1"
    assert mapping["owner_schemas"]["research_priority"] == "v4"
    assert mapping["database_identity"]["database"] == "market_research"


def test_pg_contract_mapping_fails_closed_for_namespace_mismatch(tmp_path):
    with pytest.raises(WorkspaceOwnerMappingError, match="WORKSPACE_OWNER_MAPPING_NOT_AUTHORIZED"):
        resolve_workspace_owner_mapping_document(
            root=tmp_path, trade_date="2026-10-16", selected_model_namespace_id="other-workspace",
            registry=_registry(tmp_path),
        )


def test_pg_contract_mapping_survives_checkout_relocation(monkeypatch, tmp_path):
    first = tmp_path / "drive-a" / "repo"
    moved = tmp_path / "drive-b" / "repo"
    for checkout in (first, moved):
        (checkout / ".git").mkdir(parents=True)
        (checkout / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = https://github.com/NanOns/a-share-market-structure-research.git\n',
            encoding="utf-8",
        )
    from workbench_db import v4_native
    monkeypatch.setattr(v4_native, "workspace_schema", v4_native._legacy_workspace_schema)
    registry = _registry(first)
    registry["mappings"][0]["logical_workspace_id"] = workspace_namespace_identity(
        first, "publication"
    )["logical_workspace_id"]

    mapping = resolve_workspace_owner_mapping_document(
        root=moved, trade_date="2026-10-16", selected_model_namespace_id="workspace-main",
        registry=registry,
    )

    assert mapping["logical_workspace_id"] == workspace_namespace_identity(moved, "publication")["logical_workspace_id"]
