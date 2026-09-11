"""Record the fail-closed M14-06 Dragon-Tiger list capability gate."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.lh_list_capability import build_lh_list_view


REGISTRY = ROOT / "config/m14_source_registry_v1.json"
CONTRACT = ROOT / "docs/M14_LH_LIST_CONTRACT_V1.md"
VIEW_PATH = ROOT / "data/online/m14_personal/views/m14_06_lh_list_view_v1.json"
RECEIPT = ROOT / "reports/upgrade_m14/m14_06_lh_list_receipt_20260911.json"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    dataset = next(item for item in registry["datasets"] if item["dataset"] == "LH_LIST")
    view = build_lh_list_view([], source_status=dataset["status"])
    atomic_json(VIEW_PATH, view)
    acceptance_ok = (
        dataset["status"] == "UNAVAILABLE"
        and view["capability_status"] == "UNAVAILABLE"
        and view["unavailable_reason"] == "NO_VERIFIED_LH_SOURCE"
        and view["items"] == []
        and view["batch_id"] is None
    )
    receipt = {
        "receipt_id": "M14-06-LH-LIST-20260911",
        "stage": "M14-06-LH-LIST",
        "contract_id": "M14_LH_LIST_V1_0",
        "contract": "docs/M14_LH_LIST_CONTRACT_V1.md",
        "status": "DEGRADED_PASS" if acceptance_ok else "BLOCKED",
        "release_ready": False,
        "scope": "低优先龙虎榜能力门、交易日/发布时间/来源映射合同和fail-closed空态",
        "evidence": {
            "registry_dataset_status": dataset["status"],
            "view_path": str(VIEW_PATH),
            "view_sha256": hashlib.sha256(VIEW_PATH.read_bytes()).hexdigest(),
            "capability_status": view["capability_status"],
            "unavailable_reason": view["unavailable_reason"],
            "items": len(view["items"]),
            "network_calls": 0,
            "production_tables_written": False,
            "lh_list_evidence_type_enabled": False,
            "mainline_or_queue_scoring_changed": False,
            "local_snapshot_mutated": False,
        },
        "independent_audit_items": [
            {
                "item": "M14-06-LH-SOURCE-AUTHORIZATION",
                "status": "OPEN_GATE",
                "scope": "龙虎榜来源许可、交易日和发布时间证据",
                "acceptance": "来源成熟并完成条款、映射、观察样本后才可启用",
            },
            {
                "item": "M14-06-LH-MAPPING-UNITS",
                "status": "OPEN_GATE",
                "scope": "席位/买卖字段、金额单位和证券代码映射",
                "acceptance": "字段与单位可追溯，未知不填0，不参与主线或队列评分",
            },
        ],
        "guardrails": {
            "tdx_inputs_modified": False,
            "external_adjustment_service_used": False,
            "future_data_used": False,
            "automated_trading_added": False,
            "probability_claims_added": False,
            "local_snapshot_mutated": False,
            "publication_enabled": False,
        },
        "acceptance": "DEGRADED_PASS: 龙虎榜能力独立登记并保持UNAVAILABLE；无稳定来源则不抓取、不启用LH_LIST evidence_type、不参与主线或队列综合评分",
        "next_stage": "M15",
        "next_stage_contract": "按最新M15整合与正式切换设计，逐能力汇总M14状态；不得把DEGRADED_PASS误报为M14完整可用",
        "next_stage_requires_manual_start": True,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "capability_status": view["capability_status"], "unavailable_reason": view["unavailable_reason"]}, ensure_ascii=False))
    return 0 if acceptance_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
