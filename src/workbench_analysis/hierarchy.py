"""Versioned local TDX sector hierarchy materialisation.

The hierarchy is built once from the local, already-staged TDX membership
inputs and then read by the API through an analysis-snapshot binding.  A
changed source creates a new immutable hierarchy version; existing snapshots
continue to point at the version that explained them.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import pandas as pd


CONTRACT_VERSION = "TDX_SECTOR_HIERARCHY_V1_1"


class HierarchyError(ValueError):
    pass


def _code(value: Any, sector_id: Any) -> str:
    text = "" if value is None else str(value).strip()
    if text and text.lower() != "nan":
        return text
    return str(sector_id or "").split(":", 1)[-1]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _semantic_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return only the immutable tree semantics used by H(contract, nodes)."""

    result = []
    for row in rows:
        parent = row.get("parent_sector_id")
        if parent is None or str(parent).lower() == "nan":
            parent = None
        result.append(
            {
                "sector_type": str(row["sector_type"]),
                "sector_id": str(row["sector_id"]),
                "parent_sector_id": parent,
                "hierarchy_level_code": str(row["hierarchy_level_code"]),
                "relation_basis": str(row["relation_basis"]),
            }
        )
    return sorted(result, key=lambda value: (value["sector_type"], value["sector_id"]))


def hierarchy_semantic_digest(rows: Sequence[Mapping[str, Any]], contract_id: str = CONTRACT_VERSION) -> str:
    payload = {"contract_id": contract_id, "nodes": _semantic_rows(rows)}
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


def _source_digest(source_hashes: Mapping[str, str], source_path: str, rows: Sequence[Mapping[str, Any]]) -> str:
    """Hash source observation evidence, never tree semantics."""

    payload = {
        "source_hashes": dict(sorted(source_hashes.items())),
        "source_path": source_path,
        "observed_node_count": len(rows),
    }
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


def build_hierarchy_nodes(
    memberships: pd.DataFrame,
    *,
    source_hashes: Mapping[str, str],
    source_path: str = "data/input_staging/metadata/*/T0002/hq_cache/tdxhy.cfg",
) -> tuple[str, pd.DataFrame, str]:
    """Return a deterministic version id, nodes and source digest."""
    required = {"sector_id", "sector_name", "sector_type"}
    missing = sorted(required - set(memberships.columns))
    if missing:
        raise HierarchyError("HIERARCHY_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    source = memberships.copy()
    source["sector_type"] = source["sector_type"].astype(str).str.upper()
    source["sector_id"] = source["sector_id"].astype(str)
    source["sector_name"] = source["sector_name"].astype(str)
    if "sector_code" not in source:
        source["sector_code"] = source.apply(lambda row: _code(None, row["sector_id"]), axis=1)
    source["sector_code"] = source.apply(lambda row: _code(row.get("sector_code"), row["sector_id"]), axis=1)
    sectors = source[["sector_type", "sector_id", "sector_code", "sector_name"]].drop_duplicates()
    sectors = sectors.sort_values(["sector_type", "sector_code", "sector_id"], kind="mergesort")

    rows: list[dict[str, Any]] = []
    for sector_type, group in sectors.groupby("sector_type", sort=True):
        codes = set(group["sector_code"].astype(str))
        for item in group.to_dict("records"):
            code = str(item["sector_code"])
            parent_code = None
            parent_candidates = [candidate for candidate in codes if len(candidate) < len(code) and code.startswith(candidate)]
            if sector_type == "INDUSTRY" and parent_candidates:
                parent_code = max(parent_candidates, key=len)
            parent = group[group["sector_code"].eq(parent_code)] if parent_code else group.iloc[0:0]
            parent_id = str(parent.iloc[0]["sector_id"]) if not parent.empty else None
            parent_name = str(parent.iloc[0]["sector_name"]) if not parent.empty else None
            if sector_type == "INDUSTRY":
                level = "LEAF" if parent_code else "ROOT"
                relation = "TDX_CODE_PREFIX_LONGEST_EXISTING" if parent_code else "TDX_CODE_PREFIX_ROOT"
            else:
                level = "FLAT"
                relation = "TDX_SOURCE_NO_AUDITED_PARENT"
            rows.append(
                {
                    "sector_type": sector_type,
                    "sector_id": str(item["sector_id"]),
                    "sector_code": code,
                    "sector_name": str(item["sector_name"]),
                    "parent_sector_id": parent_id,
                    "parent_sector_name": parent_name,
                    "hierarchy_level_code": level,
                    "relation_basis": relation,
                    "source_path": source_path,
                    "contract_id": CONTRACT_VERSION,
                }
            )
    rows = sorted(rows, key=lambda value: (value["sector_type"], value["sector_code"], value["sector_id"]))
    semantic_digest = hierarchy_semantic_digest(rows, CONTRACT_VERSION)
    source_digest = _source_digest(source_hashes, source_path, rows)
    version = "tdx-hierarchy-v1.1-" + semantic_digest[:16]
    result = pd.DataFrame(rows)
    if not result.empty:
        result["hierarchy_version"] = version
    return version, result, source_digest


def _find_existing_semantic_version(connection: Any, semantic_digest: str) -> tuple[str, int] | None:
    rows = connection.execute(
        """
        SELECT v.hierarchy_version, v.contract_id, v.created_at,
               n.sector_type, n.sector_id, n.parent_sector_id,
               n.hierarchy_level_code, n.relation_basis
        FROM tdx_sector_hierarchy_versions v
        JOIN tdx_sector_hierarchy_nodes n USING (hierarchy_version)
        ORDER BY v.created_at DESC, v.hierarchy_version, n.sector_type, n.sector_id
        """
    ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for version, contract_id, created_at, sector_type, sector_id, parent_id, level, relation in rows:
        record = grouped.setdefault(
            str(version),
            {"contract_id": str(contract_id), "created_at": created_at, "nodes": []},
        )
        record["nodes"].append(
            {
                "sector_type": sector_type,
                "sector_id": sector_id,
                "parent_sector_id": parent_id,
                "hierarchy_level_code": level,
                "relation_basis": relation,
            }
        )
    matches = []
    for version, record in grouped.items():
        if hierarchy_semantic_digest(record["nodes"], record["contract_id"]) == semantic_digest:
            count = len(record["nodes"])
            matches.append((record["created_at"], version, count))
    if not matches:
        return None
    _, version, count = max(matches, key=lambda item: (item[0], item[1]))
    return version, count


def ensure_hierarchy(
    connection: Any,
    memberships: pd.DataFrame,
    *,
    source_hashes: Mapping[str, str],
    source_path: str,
    now: datetime,
) -> tuple[str, str, int]:
    """Insert a new immutable hierarchy version when the source changed."""
    version, nodes, source_digest = build_hierarchy_nodes(
        memberships, source_hashes=source_hashes, source_path=source_path
    )
    existing = connection.execute(
        "select hierarchy_version from tdx_sector_hierarchy_versions where hierarchy_version=?", [version]
    ).fetchone()
    if existing:
        count = connection.execute(
            "select count(*) from tdx_sector_hierarchy_nodes where hierarchy_version=?", [version]
        ).fetchone()[0]
        return version, source_digest, int(count)
    semantic_existing = _find_existing_semantic_version(connection, hierarchy_semantic_digest(nodes.to_dict("records"), CONTRACT_VERSION))
    if semantic_existing:
        return semantic_existing[0], source_digest, semantic_existing[1]
    connection.execute(
        "insert into tdx_sector_hierarchy_versions values (?,?,?,?,?,?,?)",
        [version, CONTRACT_VERSION, source_path, _json(dict(sorted(source_hashes.items()))), source_digest, now, now],
    )
    def nullable(value: Any) -> Any:
        try:
            return None if value is None or bool(pd.isna(value)) else value
        except (TypeError, ValueError):
            return value

    rows = [
        (
            row["hierarchy_version"],
            row["sector_type"],
            row["sector_id"],
            row["sector_code"],
            row["sector_name"],
            nullable(row["parent_sector_id"]),
            nullable(row["parent_sector_name"]),
            row["hierarchy_level_code"],
            row["relation_basis"],
            row["source_path"],
            source_digest,
            row["contract_id"],
        )
        for row in nodes.to_dict("records")
    ]
    connection.executemany("insert into tdx_sector_hierarchy_nodes values (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return version, source_digest, len(rows)


@dataclass(frozen=True)
class ParentMember:
    security_id: str
    source_kinds: tuple[str, ...]


class HierarchyMembershipResolver:
    """Batch parent-member resolver with a date-free cache key."""

    SEMANTIC_VERSION = "hierarchy-parent-members-v3-v1"

    def __init__(self, connection: Any):
        self.connection = connection
        self._cache: dict[tuple[int, str, str, str], dict[str, tuple[ParentMember, ...]]] = {}

    def cache_key(
        self,
        relation_revision: int,
        hierarchy_version: str,
        *,
        semantic_version: str = SEMANTIC_VERSION,
        display_universe_version: str = "ALL",
    ) -> tuple[int, str, str, str]:
        return int(relation_revision), str(hierarchy_version), str(semantic_version), str(display_universe_version)

    def parent_members(
        self,
        source_scope: str,
        relation_revision: int,
        hierarchy_version: str,
        parent_sector_id: str,
        *,
        semantic_version: str = SEMANTIC_VERSION,
        display_universe_version: str = "ALL",
        display_security_ids: set[str] | None = None,
    ) -> tuple[ParentMember, ...]:
        key = self.cache_key(
            relation_revision,
            hierarchy_version,
            semantic_version=semantic_version,
            display_universe_version=display_universe_version,
        )
        all_members = self._resolve_all(source_scope, relation_revision, hierarchy_version, key)
        members = all_members.get(str(parent_sector_id), ())
        if display_security_ids is None:
            return members
        allowed = {str(value).upper() for value in display_security_ids}
        return tuple(item for item in members if item.security_id in allowed)

    def _resolve_all(
        self,
        source_scope: str,
        relation_revision: int,
        hierarchy_version: str,
        key: tuple[int, str, str, str],
    ) -> dict[str, tuple[ParentMember, ...]]:
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        nodes = self.connection.execute(
            """
            SELECT sector_type, sector_id, parent_sector_id, hierarchy_level_code
            FROM tdx_sector_hierarchy_nodes
            WHERE hierarchy_version=?
            ORDER BY sector_type, sector_id
            """,
            [hierarchy_version],
        ).fetchall()
        children_by_parent: dict[str, set[str]] = defaultdict(set)
        parent_ids: set[str] = set()
        for sector_type, sector_id, parent_id, level in nodes:
            if str(sector_type).upper() != "INDUSTRY" or level != "LEAF" or not parent_id:
                continue
            parent = str(parent_id)
            children_by_parent[parent].add(str(sector_id))
            parent_ids.add(parent)
        wanted = sorted(parent_ids | {child for children in children_by_parent.values() for child in children})
        if not wanted:
            self._cache[key] = {}
            return {}
        placeholders = ",".join("?" for _ in wanted)
        rows = self.connection.execute(
            f"""
            SELECT sector_id, security_id, source_kind
            FROM relation_edge_intervals
            WHERE source_scope=? AND sector_id IN ({placeholders})
              AND from_revision<=?
              AND (to_revision IS NULL OR ?<to_revision)
            ORDER BY sector_id, security_id, source_kind
            """,
            [source_scope, *wanted, relation_revision, relation_revision],
        ).fetchall()
        parent_members: dict[str, dict[str, set[str]]] = {
            parent: defaultdict(set) for parent in sorted(children_by_parent)
        }
        child_to_parents: dict[str, set[str]] = defaultdict(set)
        for parent, children in children_by_parent.items():
            for child in children:
                child_to_parents[child].add(parent)
        for sector_id, security_id, source_kind in rows:
            sector = str(sector_id)
            security = str(security_id).upper()
            kind = str(source_kind).upper()
            for parent in child_to_parents.get(sector, ()):
                parent_members[parent][security].add("DERIVED")
            if sector in parent_members:
                parent_members[sector][security].add(kind)
        result = {
            parent: tuple(
                ParentMember(security_id=security, source_kinds=tuple(sorted(kinds)))
                for security, kinds in sorted(values.items())
            )
            for parent, values in sorted(parent_members.items())
        }
        self._cache[key] = result
        return result


def load_bound_nodes(connection: Any, snapshot_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Read the immutable hierarchy bound to an analysis snapshot."""
    rows = connection.execute(
        """
        select n.sector_type,n.sector_id,n.sector_code,n.sector_name,
               n.parent_sector_id,n.parent_sector_name,n.hierarchy_level_code,
               n.relation_basis,n.hierarchy_version,n.source_hash,n.contract_id
          from analysis_snapshot_hierarchy b
          join tdx_sector_hierarchy_nodes n using(hierarchy_version)
         where b.snapshot_id=?
        """,
        [snapshot_id],
    ).fetchall()
    names = (
        "sector_type",
        "sector_id",
        "sector_code",
        "sector_name",
        "parent_sector_id",
        "parent_sector_name",
        "hierarchy_level_code",
        "relation_basis",
        "hierarchy_version",
        "source_hash",
        "contract_id",
    )
    return {(str(row[0]), str(row[1])): dict(zip(names, row)) for row in rows}
