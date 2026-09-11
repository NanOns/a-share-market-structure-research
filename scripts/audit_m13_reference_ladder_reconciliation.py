"""Produce the independent-readable M13 reference/ladder set reconciliation.

The audit is read-only.  It explains every set difference under the current
universe contract and deliberately leaves scope decisions for independent
review; it does not silently add securities to the ladder.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
REPORT_PATH = ROOT / "reports/upgrade_m13/m13_reference_ladder_reconciliation_20260911.md"

import sys
sys.path.insert(0, str(ROOT / "src"))
from workbench_service.universe import STATISTICAL_SCOPE_CONTRACT_ID, is_workbench_statistical_security_id


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _active_snapshot(connection: duckdb.DuckDBPyConnection) -> tuple[str, str]:
    row = connection.execute(
        "select snapshot_id from publication_analysis_snapshots where domain='LOCAL_RECONSTRUCTED' order by bound_at desc limit 1"
    ).fetchone()
    if not row:
        raise RuntimeError("M13_ACTIVE_PUBLICATION_MISSING")
    snapshot_id = str(row[0])
    basis = connection.execute(
        """
        select s.basis_json
          from analysis_snapshot_entries e
          join analysis_slices s on s.slice_id=e.slice_id
         where e.snapshot_id=? and e.domain='limit_ladder'
         order by e.trade_date
         limit 1
        """,
        [snapshot_id],
    ).fetchone()
    if not basis:
        raise RuntimeError("M13_ACTIVE_LADDER_MISSING")
    registry_id = json.loads(str(basis[0])).get("reference_registry_snapshot_id")
    if not registry_id:
        raise RuntimeError("M13_REFERENCE_REGISTRY_ID_MISSING_FROM_SLICE")
    return snapshot_id, str(registry_id)


def build(db_path: str | Path = DB_PATH, report_path: str | Path = REPORT_PATH, registry_snapshot_id: str | None = None) -> dict:
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        snapshot_id, active_registry_id = _active_snapshot(connection)
        registry_id = registry_snapshot_id or os.environ.get("M13_REFERENCE_REGISTRY_SNAPSHOT_ID") or active_registry_id
        reference = {
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                """
                select m.security_id,m.trade_date
                  from market_reference_daily m
                  join analysis_snapshot_entries e
                    on e.snapshot_id=? and e.domain='market_reference'
                   and e.slice_id=m.slice_id and e.trade_date=m.trade_date
                 where m.contract_id='REFERENCE_CAPABILITY_V1_1'
                """,
                [registry_id],
            ).fetchall()
        }
        ladder = {
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                """
                select l.security_id,l.trade_date
                  from limit_ladder_daily l
                  join analysis_snapshot_entries e
                    on e.snapshot_id=? and e.domain='limit_ladder'
                   and e.slice_id=l.slice_id and e.trade_date=l.trade_date
                """,
                [snapshot_id],
            ).fetchall()
        }
    finally:
        connection.close()

    ref_only = sorted(reference - ladder)
    ladder_only = sorted(ladder - reference)
    rows = []
    for security_id, trade_date in ref_only:
        in_scope = is_workbench_statistical_security_id(security_id, ROOT)
        rows.append((security_id, trade_date, "IN_SCOPE" if in_scope else "OUT_OF_SCOPE", None if in_scope else f"SECURITY_SCOPE_EXCLUDED:{STATISTICAL_SCOPE_CONTRACT_ID}"))
    for security_id, trade_date in ladder_only:
        rows.append((security_id, trade_date, "LADDER_ONLY", "LADDER_HAS_NO_REFERENCE_ROW"))

    lines = [
        "# M13 参考集合与梯队集合对账（R3 补充审计材料）",
        "",
        "生成目的：解释 reference registry 与 M13 limit ladder 的双向差集。此文件是审计证据，不授予 `EXTERNAL_AUDIT_PASS`，也不擅自改变统计范围。",
        "",
        f"- active M13 snapshot: `{snapshot_id}`",
        f"- consumed reference registry: `{registry_id}`",
        f"- statistical scope contract: `{STATISTICAL_SCOPE_CONTRACT_ID}`",
        f"- reference rows: {len(reference)}",
        f"- ladder rows: {len(ladder)}",
        f"- reference-only rows: {len(ref_only)}",
        f"- ladder-only rows: {len(ladder_only)}",
        "",
        "## 差集明细",
        "",
        "| security_id | trade_date | classification | explanation |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| `{sid}` | `{day}` | `{classification}` | `{reason or '待独立确认'}` |" for sid, day, classification, reason in rows)
    if not rows:
        lines.append("| — | — | — | 双向差集为空 |")
    lines.extend(
        [
            "",
            "## 当前验收结论",
            "",
            f"- 双向差集已被程序完整列出；本次共 {len(rows)} 条，不允许用测试数量替代集合恒等式。",
            "- reference-only 行只有在统计范围合同明确允许时才能进入梯队；本次不自动放宽前缀。",
            "- `M13-EXT-009-R1`：请外部审计确认 `SZ.201872` 是否应纳入 `workbench-universe-v2.2` 的 A 股统计范围；在确认前保留排除状态。",
            "- 若范围结论改变，必须升级 universe contract、生成新 registry/M13 identity，并重放差异；不得修改旧 snapshot。",
        ]
    )
    payload = {
        "active_snapshot_id": snapshot_id,
        "reference_registry_snapshot_id": registry_id,
        "statistical_scope_contract": STATISTICAL_SCOPE_CONTRACT_ID,
        "reference_rows": len(reference),
        "ladder_rows": len(ladder),
        "reference_only": [{"security_id": sid, "trade_date": day, "in_scope": is_workbench_statistical_security_id(sid, ROOT)} for sid, day in ref_only],
        "ladder_only": [{"security_id": sid, "trade_date": day} for sid, day in ladder_only],
        "audit_item": "M13-EXT-009-R1",
    }
    _write_atomic(Path(report_path).resolve(), "\n".join(lines) + "\n")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry")
    args = parser.parse_args()
    print(json.dumps(build(registry_snapshot_id=args.registry), ensure_ascii=False, indent=2))
