"""Exact root-to-PG namespace mapping; publication T0 is never a resolver."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .v4_native import workspace_namespace_identity

CONTRACT_ID = "V4_PG_WORKSPACE_OWNER_MAPPING_R1"
CONTRACT_VERSION = "1.0.0"
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "v4_pg_workspace_owner_authority_r1.json"
_SCHEMA = re.compile(r"^v4_[a-z0-9_]{1,56}$")


class WorkspaceOwnerMappingError(ValueError):
    pass


def resolve_workspace_owner_mapping(
    *, root: str | Path, trade_date: str, selected_model_namespace_id: str,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve only an explicitly authorized historical workspace mapping."""
    try:
        target = date.fromisoformat(trade_date)
    except (TypeError, ValueError) as exc:
        raise WorkspaceOwnerMappingError("WORKSPACE_MAPPING_TRADE_DATE_INVALID") from exc
    if target.isoformat() != trade_date:
        raise WorkspaceOwnerMappingError("WORKSPACE_MAPPING_TRADE_DATE_NONCANONICAL")
    if not isinstance(selected_model_namespace_id, str) or not selected_model_namespace_id.strip():
        raise WorkspaceOwnerMappingError("WORKSPACE_MAPPING_NAMESPACE_REQUIRED")
    identity = workspace_namespace_identity(root, "publication")
    path = Path(registry_path) if registry_path is not None else REGISTRY_PATH
    try:
        registry = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_REGISTRY_UNAVAILABLE") from exc
    if (not isinstance(registry, Mapping)
            or registry.get("contract_id") != "V4_PG_WORKSPACE_OWNER_MAPPING_REGISTRY_R1"
            or registry.get("contract_version") != "1.0.0"):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_REGISTRY_INVALID")
    entries = registry.get("mappings")
    if not isinstance(entries, list):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_REGISTRY_INVALID")
    matches = [entry for entry in entries if isinstance(entry, Mapping)
               and entry.get("root_identity_sha256") == identity["root_identity_sha256"]]
    if not matches:
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_UNAVAILABLE")
    if len(matches) != 1:
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_AMBIGUOUS")
    entry = matches[0]
    if (entry.get("status") != "APPROVED" or entry.get("model_namespace_id") != selected_model_namespace_id
            or not isinstance(entry.get("authorized_by"), str) or not entry["authorized_by"].strip()
            or not isinstance(entry.get("authorization_reference"), str) or not entry["authorization_reference"].strip()):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_NOT_AUTHORIZED")
    try:
        valid_from = date.fromisoformat(entry["valid_from"])
        valid_to = date.fromisoformat(entry["valid_to"]) if entry.get("valid_to") else None
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_VALIDITY_INVALID") from exc
    if valid_from.isoformat() != entry["valid_from"] or (valid_to and valid_to.isoformat() != entry["valid_to"]):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_VALIDITY_INVALID")
    if target < valid_from or (valid_to and target > valid_to):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_MAPPING_OUT_OF_SCOPE")
    owner_schemas = entry.get("owner_schemas")
    if not isinstance(owner_schemas, Mapping) or set(owner_schemas) != {"research_priority", "operational_risk", "sector_lifecycle"}:
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_SCHEMA_MAPPING_INCOMPLETE")
    if any(not isinstance(schema, str) or not _SCHEMA.fullmatch(schema) for schema in owner_schemas.values()):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_SCHEMA_INVALID")
    database_identity = entry.get("database_identity")
    if (not isinstance(database_identity, Mapping)
            or set(database_identity) != {"database", "database_oid", "host", "port"}
            or database_identity.get("database") != "market_research"
            or database_identity.get("host") != "127.0.0.1"
            or database_identity.get("port") != 5432):
        raise WorkspaceOwnerMappingError("WORKSPACE_OWNER_DATABASE_IDENTITY_INVALID")
    return {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "root_identity_sha256": identity["root_identity_sha256"],
        "model_namespace_id": entry["model_namespace_id"],
        "database_identity": dict(database_identity), "owner_schemas": dict(owner_schemas),
        "valid_from": valid_from.isoformat(), "valid_to": valid_to.isoformat() if valid_to else None,
        "authorized_by": entry["authorized_by"],
        "authorization_reference": entry["authorization_reference"],
    }
