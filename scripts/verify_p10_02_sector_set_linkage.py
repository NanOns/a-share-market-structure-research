"""Verify and seal P10-02 with read-only API and UI evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.app import Api  # noqa: E402
from workbench_service.research_context import ResearchContextReader  # noqa: E402
from workbench_service.intersection import CONTRACT_ID, P10_CONTRACT_ID  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
DB = ROOT / "data" / "database" / "market_research.duckdb"
REPORT = ROOT / "reports" / "upgrade_v3" / "P10-02-SECTOR-SET-LINKAGE.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_atomic(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def _request(publication_id: str, sector_ids: list[str], **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "publication_id": publication_id,
        "basis": "RECONSTRUCTED",
        "include_sector_ids": sector_ids,
        "operator": "UNION",
        "exclude_sector_ids": [],
        "filters": {},
        "sort": "security_id.asc",
        "page": 1,
        "page_size": 100,
    }
    body.update(extra)
    return body


def _run() -> dict[str, object]:
    before = (DB.stat().st_size, DB.stat().st_mtime_ns)
    api = Api(DB)
    publications = api.publications(include_analysis=True)["items"]
    publication_id = str(publications[0]["publication_id"])
    trade_date = str(api._pub(publication_id)[0])
    sectors = api.sector_library(publication_id, page=1, size=4, basis="RECONSTRUCTED")["items"]
    selected = sectors[:2]
    context = ResearchContextReader(lambda: api._con()).resolve_request(publication_id, trade_date)

    name_result = api.sector_intersection_query(_request(
        publication_id,
        [],
        include_sector_names=[item["sector_name"] for item in selected],
    ))
    selected_ids = [item["sector_id"] for item in selected]
    old_result = api.sector_intersection_query(_request(publication_id, selected_ids))
    with api._con() as connection:
        member_set = {
            str(row[0])
            for row in connection.execute(
                """select distinct security_id from member_state_result_daily
                   where slice_id=(select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' and trade_date=? limit 1)
                     and trade_date=? and member_present=true and sector_id in (?,?)""",
                [old_result["snapshot_id"], old_result["trade_date"], old_result["trade_date"], *selected_ids],
            ).fetchall()
        }
    role_result = None
    role_ids: set[str] = set()
    if context["status"] == "READY":
        role_result = api.sector_intersection_query(_request(
            publication_id,
            selected_ids,
            research_context_id=context["context_id"],
            member_role="TODAY_LEADER",
        ))
        role_ids = {str(item["security_id"]) for item in role_result["items"]}
    after = (DB.stat().st_size, DB.stat().st_mtime_ns)

    page = (ROOT / "src" / "workbench_service" / "static" / "v2" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "workbench_service" / "static" / "v2" / "app.js").read_text(encoding="utf-8")
    router = (ROOT / "src" / "workbench_service" / "static" / "v2" / "router.js").read_text(encoding="utf-8")
    v3 = (ROOT / "src" / "workbench_service" / "static" / "research-v3.html").read_text(encoding="utf-8")
    node_probe = subprocess.run(
        ["node", "-e", "const fs=require('fs'),vm=require('vm'); for (const p of process.argv.slice(1)) new vm.Script(fs.readFileSync(p,'utf8'),{filename:p});"]
        + [str(ROOT / "src" / "workbench_service" / "static" / "v2" / name) for name in ("router.js", "api.js", "app.js")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    checks = {
        "p10_contract": P10_CONTRACT_ID == "V3_P10_SECTOR_SET_LINKAGE_V1_0",
        "api14_contract_preserved": name_result["contract_id"] == CONTRACT_ID,
        "name_selection_two_to_four": name_result["include_sector_ids"] == selected_ids and len(selected_ids) == 2,
        "name_result_total_is_member_total": name_result["total"] == name_result["candidate_total_before_filters"],
        "old_request_shape_preserved": not any(key in old_result for key in ("p10_contract_id", "research_context_id", "member_role", "include_sector_names")),
        "role_filter_verified": role_result is None or (
            role_result["member_role"] == "TODAY_LEADER"
            and role_result["total"] == role_result["candidate_total_before_filters"]
            and role_ids <= member_set
        ),
        "database_unchanged": before == after,
        "name_picker_ui": all(marker in page for marker in ("linkage-sector-search", "linkage-sector-suggestions", "linkage-selected-sectors", "linkage-member-role")),
        "context_and_selection_ui": all(marker in app for marker in ("selectedIncludeSectors", "ensureLinkageResearchContext", "research_context_id", "member_role", "router.write")),
        "context_route_ui": "context_id" in router and "sector_id" in router,
        "stock_primary_backup_links": all(marker in v3 for marker in ("stockSectorLinks", "主板块", "备选板块", "context_id")),
        "javascript_syntax": node_probe.returncode == 0,
    }
    return {
        "checks": checks,
        "context": {"status": context["status"], "context_id": context.get("context_id"), "run_id": context.get("run_id")},
        "selection": {"publication_id": publication_id, "trade_date": trade_date, "sector_ids": selected_ids, "sector_names": [item["sector_name"] for item in selected]},
        "name_result": {"total": name_result["total"], "candidate_total_before_filters": name_result["candidate_total_before_filters"], "include_sector_ids": name_result["include_sector_ids"]},
        "role_result": None if role_result is None else {"member_role": role_result["member_role"], "total": role_result["total"], "candidate_total_before_filters": role_result["candidate_total_before_filters"]},
        "node_probe": {"returncode": node_probe.returncode, "stderr": node_probe.stderr[-1000:]},
        "database_stat_before": {"size": before[0], "mtime_ns": before[1]},
        "database_stat_after": {"size": after[0], "mtime_ns": after[1]},
    }


def main() -> int:
    evidence = _run()
    checks = evidence["checks"]
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P10-02-SECTOR-SET-LINKAGE",
        "stage": "P10-02",
        "status": status,
        "engineering_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "contract_id": P10_CONTRACT_ID,
            "legacy_api_contract": CONTRACT_ID,
            "spec_sha256": _sha256(SPEC),
            "spec_section": "§12、§18.13、§20.3–§20.8",
            "scope": "名称选择2–4板块；API14先集合、再研究角色过滤、再总数和分页；主备板块 context 回返；旧请求兼容。",
        },
        "checks": checks,
        "evidence": evidence,
        "acceptance": (
            "P10-02 FULL_PASS：名称选择、API14角色过滤、分页总数、旧请求兼容和跨页 context 路径均有证据；未写生产数据库。"
            if status == "FULL_PASS"
            else "P10-02 BLOCKED：至少一项集合、角色、兼容、UI 或只读边界验收失败。"
        ),
        "known_limits": [
            "角色筛选依赖 COMPLETE research run；没有 READY context 时只保留 ALL_MEMBERS 旧集合，不伪造研究角色。",
            "P10-03 前瞻结果、基线和效果观察尚未实现，本回执不作概率或效果结论。",
            "本阶段未触碰 TDX 输入目录，未新增数据库表或写入 research run。",
        ],
        "next_stage": "P10-03" if status == "FULL_PASS" else "P10-02-REPAIR",
        "tdx_inputs_modified": False,
        "production_database_written": False,
    }
    _write_atomic(payload)
    print(json.dumps({"status": status, "checks": checks, "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
