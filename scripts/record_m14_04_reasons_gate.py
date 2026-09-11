"""Record the fail-closed M14-04 reasons capability gate."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.external_evidence import build_external_evidence_view


REGISTRY = ROOT / "config/m14_source_registry_v1.json"
CONTRACT = ROOT / "docs/M14_EXTERNAL_EVIDENCE_CONTRACT_V1.md"
VIEW_PATH = ROOT / "data/online/m14_personal/views/m14_04_external_evidence_view_v1.json"
RECEIPT = ROOT / "reports/upgrade_m14/m14_04_reasons_receipt_20260911.json"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    dataset = next(item for item in registry["datasets"] if item["dataset"] == "EXTERNAL_EVIDENCE")
    view = build_external_evidence_view([], source_status=dataset["status"])
    atomic_json(VIEW_PATH, view)
    acceptance_ok = (
        dataset["status"] == "UNAVAILABLE"
        and view["capability_status"] == "UNAVAILABLE"
        and view["unavailable_reason"] == "NO_VERIFIED_REASON_SOURCE"
        and view["items"] == []
        and view["post_hoc_items"] == []
        and view["batch_id"] is None
    )
    receipt = {
        "receipt_id": "M14-04-REASONS-20260911",
        "stage": "M14-04-REASONS",
        "contract_id": "M14_EXTERNAL_EVIDENCE_V1_0",
        "contract": "docs/M14_EXTERNAL_EVIDENCE_CONTRACT_V1.md",
        "status": "DEGRADED_PASS" if acceptance_ok else "BLOCKED",
        "release_ready": False,
        "scope": "涨停原因/外部证据能力门、时间字段合同和 fail-closed 空态",
        "evidence": {
            "registry_dataset_status": dataset["status"],
            "view_path": str(VIEW_PATH),
            "view_sha256": hashlib.sha256(VIEW_PATH.read_bytes()).hexdigest(),
            "capability_status": view["capability_status"],
            "unavailable_reason": view["unavailable_reason"],
            "items": len(view["items"]),
            "post_hoc_items": len(view["post_hoc_items"]),
            "network_calls": 0,
            "production_tables_written": False,
            "api38_enabled": False,
            "local_snapshot_mutated": False,
        },
        "independent_audit_items": [
            {
                "item": "M14-04-REASON-SOURCE-AUTHORIZATION",
                "status": "OPEN_GATE",
                "scope": "原因来源许可、正文来源和自动采集边界",
                "acceptance": "逐来源完成许可、字段、时间、正文哈希和10个交易日观察；此前保持UNAVAILABLE",
            },
            {
                "item": "M14-04-REASON-TIME-SEMANTICS",
                "status": "OPEN_GATE",
                "scope": "event_time、published_at、first_seen_at的完整性和AS_OF规则",
                "acceptance": "所有严格历史条目具备三类时间；事后补充单独分组",
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
        "acceptance": "DEGRADED_PASS: 原因能力独立登记并 fail-closed；当前无已验证来源，返回UNAVAILABLE空态，不生成原因文本、不启用API38/UI",
        "next_stage": "M14-05-QUOTES",
        "next_stage_contract": "先审计可选盘中报价来源、单位/时间/代码映射和独立报价批次；不得把热榜载荷当作报价",
        "next_stage_requires_manual_start": True,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "capability_status": view["capability_status"], "unavailable_reason": view["unavailable_reason"]}, ensure_ascii=False))
    return 0 if acceptance_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
