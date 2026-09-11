"""Audit and, with ``--apply``, bind a fixed V3 hierarchy to one legacy observation.

The default mode is read-only.  Apply mode is reserved for a stopped workbench
service after a verified backup.  This script only updates the V3 relation
observation/snapshot bindings; it never changes legacy membership rows or the
older ``analysis_snapshot_hierarchy`` table.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.hierarchy import (  # noqa: E402
    CONTRACT_VERSION,
    HierarchyMembershipResolver,
    hierarchy_semantic_digest,
)
from workbench_service.legacy_relation_import import LEGACY_SOURCE_SCOPE  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data/database/market_research.duckdb",
        help="DuckDB path; read-only unless --apply is supplied",
    )
    parser.add_argument("--trade-date", default="2026-09-10", help="legacy snapshot date to audit/bind")
    parser.add_argument("--apply", action="store_true", help="apply the verified V3 binding")
    return parser


def _tree_candidates(connection: Any) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT v.hierarchy_version, v.contract_id, v.created_at,
               n.sector_type, n.sector_id, n.parent_sector_id,
               n.hierarchy_level_code, n.relation_basis
        FROM tdx_sector_hierarchy_versions v
        JOIN tdx_sector_hierarchy_nodes n USING (hierarchy_version)
        WHERE v.contract_id=?
        ORDER BY v.created_at, v.hierarchy_version, n.sector_type, n.sector_id
        """,
        [CONTRACT_VERSION],
    ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for version, contract_id, created_at, sector_type, sector_id, parent_id, level, relation in rows:
        item = grouped.setdefault(
            str(version),
            {"hierarchy_version": str(version), "contract_id": str(contract_id), "created_at": created_at, "nodes": []},
        )
        item["nodes"].append(
            {
                "sector_type": sector_type,
                "sector_id": sector_id,
                "parent_sector_id": parent_id,
                "hierarchy_level_code": level,
                "relation_basis": relation,
            }
        )
    candidates = []
    for item in grouped.values():
        item["node_count"] = len(item["nodes"])
        item["semantic_digest"] = hierarchy_semantic_digest(item["nodes"], item["contract_id"])
        candidates.append(item)
    return sorted(candidates, key=lambda item: (item["created_at"], item["hierarchy_version"]))


def _binding(connection: Any, trade_date: date) -> tuple[Any, ...]:
    row = connection.execute(
        """
        SELECT b.legacy_membership_snapshot_id, b.observation_id, b.revision_no,
               b.hierarchy_version, b.legacy_payload_basis,
               o.source_scope, o.source_effective_date, o.hierarchy_version
        FROM relation_snapshot_bindings b
        JOIN membership_snapshots s ON s.membership_snapshot_id=b.legacy_membership_snapshot_id
        JOIN relation_observations o ON o.observation_id=b.observation_id
        WHERE s.trade_date=?
        ORDER BY b.legacy_membership_snapshot_id
        """,
        [trade_date],
    ).fetchall()
    if len(row) != 1:
        raise ValueError(f"EXPECTED_ONE_SNAPSHOT_BINDING:{trade_date}:{len(row)}")
    return row[0]


def _audit(connection: Any, trade_date: date) -> dict[str, Any]:
    candidates = _tree_candidates(connection)
    if not candidates:
        raise ValueError(f"NO_TREE_CONTRACT:{CONTRACT_VERSION}")
    target = candidates[-1]
    snapshot_id, observation_id, revision_no, bound_version, basis_value, scope, effective_date, observed_version = _binding(
        connection, trade_date
    )
    if str(scope) != LEGACY_SOURCE_SCOPE:
        raise ValueError(f"UNEXPECTED_SOURCE_SCOPE:{scope}")
    if effective_date != trade_date:
        raise ValueError(f"SOURCE_DATE_MISMATCH:{effective_date}:{trade_date}")
    basis = json.loads(str(basis_value))

    nodes = connection.execute(
        """
        SELECT sector_id, parent_sector_id
        FROM tdx_sector_hierarchy_nodes
        WHERE hierarchy_version=? AND sector_type='INDUSTRY' AND hierarchy_level_code='LEAF'
        """,
        [target["hierarchy_version"]],
    ).fetchall()
    children_by_parent: dict[str, set[str]] = defaultdict(set)
    for child, parent in nodes:
        if parent:
            children_by_parent[str(parent)].add(str(child))
    edge_rows = connection.execute(
        """
        SELECT sector_id, security_id
        FROM relation_edge_intervals
        WHERE source_scope=? AND from_revision<=?
          AND (to_revision IS NULL OR ?<to_revision)
        """,
        [LEGACY_SOURCE_SCOPE, revision_no, revision_no],
    ).fetchall()
    direct_by_sector: dict[str, set[str]] = defaultdict(set)
    for sector_id, security_id in edge_rows:
        direct_by_sector[str(sector_id)].add(str(security_id).upper())
    expected: dict[str, set[str]] = {}
    for parent, children in children_by_parent.items():
        expected[parent] = set(direct_by_sector.get(parent, set()))
        for child in children:
            expected[parent].update(direct_by_sector.get(child, set()))

    resolver = HierarchyMembershipResolver(connection)
    actual = {
        parent: {item.security_id for item in resolver.parent_members(LEGACY_SOURCE_SCOPE, revision_no, target["hierarchy_version"], parent)}
        for parent in sorted(children_by_parent)
    }
    mismatches = {
        parent: {"expected": sorted(expected[parent]), "actual": sorted(actual.get(parent, set()))}
        for parent in sorted(expected)
        if expected[parent] != actual.get(parent, set())
    }
    derived_parent_count = sum(len(values) for values in expected.values())
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "trade_date": str(trade_date),
        "snapshot_id": str(snapshot_id),
        "observation_id": str(observation_id),
        "revision_no": int(revision_no),
        "existing_snapshot_hierarchy_version": bound_version,
        "existing_observation_hierarchy_version": observed_version,
        "target_hierarchy_version": target["hierarchy_version"],
        "target_tree_node_count": target["node_count"],
        "target_tree_semantic_digest": target["semantic_digest"],
        "tree_candidates": [
            {key: value for key, value in item.items() if key != "nodes"} for item in candidates
        ],
        "parent_count": len(expected),
        "derived_parent_member_count": derived_parent_count,
        "legacy_row_count": int(basis["legacy_row_count"]),
        "legacy_direct_edge_count": int(basis["direct_edge_count"]),
        "legacy_derived_edge_count": int(basis["derived_edge_count"]),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def main() -> int:
    args = _parser().parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"DATABASE_NOT_FOUND:{database}")
    trade_date = date.fromisoformat(args.trade_date)
    with duckdb.connect(str(database), read_only=not args.apply) as connection:
        audit = _audit(connection, trade_date)
        audit["database"] = str(database)
        audit["apply"] = bool(args.apply)
        if args.apply:
            if audit["status"] != "PASS":
                print(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2, default=str))
                return 2
            connection.execute("BEGIN")
            try:
                connection.execute(
                    "UPDATE relation_snapshot_bindings SET hierarchy_version=? WHERE legacy_membership_snapshot_id=?",
                    [audit["target_hierarchy_version"], audit["snapshot_id"]],
                )
                connection.execute(
                    "UPDATE relation_observations SET hierarchy_version=? WHERE observation_id=?",
                    [audit["target_hierarchy_version"], audit["observation_id"]],
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
            audit["status"] = "APPLIED"
        print(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
