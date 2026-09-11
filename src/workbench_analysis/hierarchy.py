"""Versioned local TDX sector hierarchy materialisation.

The hierarchy is built once from the local, already-staged TDX membership
inputs and then read by the API through an analysis-snapshot binding.  A
changed source creates a new immutable hierarchy version; existing snapshots
continue to point at the version that explained them.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

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


def _source_digest(source_hashes: Mapping[str, str], rows: list[dict[str, Any]]) -> str:
    payload = {"contract_id": CONTRACT_VERSION, "source_hashes": dict(sorted(source_hashes.items())), "rows": rows}
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
    digest = _source_digest(source_hashes, rows)
    version = "tdx-hierarchy-v1.1-" + digest[:16]
    result = pd.DataFrame(rows)
    if not result.empty:
        result["hierarchy_version"] = version
    return version, result, digest


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
