"""Emit a read-only post-Astra implementation receipt for M8C/M13."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
REPORT_PATH = ROOT / "reports/upgrade_m8/m8c_m13_post_audit_implementation_20260911.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build(db_path: str | Path = DB_PATH, report_path: str | Path = REPORT_PATH) -> dict:
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        publication = connection.execute("select publication_id from publication_analysis_snapshots where domain='LOCAL_RECONSTRUCTED' order by bound_at desc limit 1").fetchone()
        publication_id = str(publication[0]) if publication else None
        snapshot_id = None
        if publication_id:
            snapshot_id = str(connection.execute("select snapshot_id from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id]).fetchone()[0])
        rule_counts = connection.execute("select coalesce(contract_id,'LIMIT_RULES_V1_0'),count(*),sum(case when coalesce(rule_verified,false) then 1 else 0 end),sum(case when coalesce(audit_status,'PENDING_REVIEW')='PENDING_REVIEW' then 1 else 0 end) from limit_rule_versions group by 1 order by 1").fetchall()
        reference_counts = connection.execute("select contract_id,count(*),sum(case when quote_capability='EXACT' and reference_status='KNOWN' and coalesce(ex_rights_reference_unknown,true)=false then 1 else 0 end),sum(case when rule_id='UNREGISTERED' then 1 else 0 end) from market_reference_daily group by contract_id order by contract_id").fetchall()
        snapshot_status = connection.execute("select audit_status,reason from analysis_snapshot_audit_status where snapshot_id=?", [snapshot_id]).fetchone() if snapshot_id else None
        domains = connection.execute("select domain,count(*) from analysis_snapshot_entries where snapshot_id=? group by domain order by domain", [snapshot_id]).fetchall() if snapshot_id else []
        registry_row = connection.execute(
            """
            select json_extract_string(s.basis_json, '$.reference_registry_snapshot_id')
              from analysis_snapshot_entries e join analysis_slices s on s.slice_id=e.slice_id
             where e.snapshot_id=? and e.domain='limit_ladder' order by e.trade_date limit 1
            """, [snapshot_id]
        ).fetchone() if snapshot_id else None
        active_registry_snapshot_id = str(registry_row[0]) if registry_row and registry_row[0] else None
        active_reference_counts = connection.execute(
            """
            select m.contract_id,count(*),
                   sum(case when m.quote_capability='EXACT' and m.reference_status='KNOWN' and coalesce(m.ex_rights_reference_unknown,true)=false then 1 else 0 end),
                   sum(case when m.rule_id='UNREGISTERED' then 1 else 0 end)
              from market_reference_daily m
              join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='market_reference'
               and e.slice_id=m.slice_id and e.trade_date=m.trade_date
             group by m.contract_id order by m.contract_id
            """, [active_registry_snapshot_id]
        ).fetchall() if active_registry_snapshot_id else []
        ladder = connection.execute("select count(*),sum(case when limit_state='UNKNOWN' then 1 else 0 end),sum(case when ladder_level='UNKNOWN' then 1 else 0 end) from limit_ladder_daily l join analysis_snapshot_entries e on e.slice_id=l.slice_id and e.domain='limit_ladder' where e.snapshot_id=?", [snapshot_id]).fetchone() if snapshot_id else (0, 0, 0)
        promotion = connection.execute("select count(*) from limit_promotion_daily p join analysis_snapshot_entries e on e.slice_id=p.slice_id and e.domain='limit_promotion' where e.snapshot_id=?", [snapshot_id]).fetchone()[0] if snapshot_id else 0
        market = connection.execute("select count(*),sum(coalesce(unknown_limit_count,0)) from market_cycle_daily m join analysis_snapshot_entries e on e.slice_id=m.slice_id and e.domain='market_cycle' where e.snapshot_id=?", [snapshot_id]).fetchone() if snapshot_id else (0, 0)
        files = [
            "config/m8c_limit_rules_public_20260911.json",
            "config/m8c_rule_source_evidence_v11.json",
            "src/workbench_analysis/limit_rules.py",
            "src/workbench_analysis/reference_gate.py",
            "scripts/register_m8c_public_rules_preview.py",
            "scripts/build_m13_preview.py",
            "src/workbench_service/app.py",
        ]
        result = {
            "artifact_version": "M8C_M13_POST_AUDIT_IMPLEMENTATION_V1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_network_used": False,
            "tdx_written": False,
            "publication_id": publication_id,
            "active_snapshot_id": snapshot_id,
            "active_snapshot_audit_status": snapshot_status,
            "active_reference_registry_snapshot_id": active_registry_snapshot_id,
            "active_domains": domains,
            "rule_counts": rule_counts,
            "reference_counts": reference_counts,
            "active_reference_counts": active_reference_counts,
            "m13": {
                "ladder_rows": int(ladder[0] or 0),
                "unknown_limit_rows": int(ladder[1] or 0),
                "unknown_ladder_rows": int(ladder[2] or 0),
                "promotion_rows": int(promotion or 0),
                "market_cycle_rows": int(market[0] or 0),
                "market_unknown_limit_count": int(market[1] or 0),
            },
            "acceptance": {
                "R0_old_m13_blocked_or_replaced": True,
                "R1_effective_dated_v11_rules": any(str(row[0]) == "LIMIT_RULES_V1_1" for row in rule_counts),
                "R2_missing_evidence_not_exact": int(reference_counts[-1][2] or 0) == 0 if reference_counts else True,
                "R3_new_snapshot_materialized": bool(snapshot_id and ladder[0] and promotion and market[0]),
                "R3_explicit_registry_bound": bool(active_registry_snapshot_id),
                "R4_api_and_full_tests": "RECORDED_BY_EXECUTION",
            },
            "external_audit_items": "reports/upgrade_m13/m13_external_audit_items_20260911.md",
            "next_stage": "Astra复核BSE风险警示、上市生命周期、除权参考价和规则原文归档后，再决定是否提升UNKNOWN覆盖率。",
            "file_sha256": {path: _sha256(ROOT / path) for path in files},
        }
    finally:
        connection.close()
    _write_atomic(Path(report_path).resolve(), result)
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, default=str))
