"""Record the fail-closed M14-05 quote capability gate."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.quotes_capability import build_quote_view


REGISTRY = ROOT / "config/m14_source_registry_v1.json"
CONTRACT = ROOT / "docs/M14_QUOTES_CONTRACT_V1.md"
VIEW_PATH = ROOT / "data/online/m14_personal/views/m14_05_quotes_view_v1.json"
RECEIPT = ROOT / "reports/upgrade_m14/m14_05_quotes_receipt_20260911.json"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    dataset = next(item for item in registry["datasets"] if item["dataset"] == "QUOTES_LATEST")
    view = build_quote_view([], source_status=dataset["status"])
    atomic_json(VIEW_PATH, view)
    acceptance_ok = (
        dataset["status"] == "NOT_VERIFIED"
        and view["capability_status"] == "NOT_VERIFIED"
        and view["unavailable_reason"] == "NO_VERIFIED_QUOTE_SOURCE"
        and view["items"] == []
        and view["batch_id"] is None
    )
    receipt = {
        "receipt_id": "M14-05-QUOTES-20260911",
        "stage": "M14-05-QUOTES",
        "contract_id": "M14_QUOTES_LATEST_V1_0",
        "contract": "docs/M14_QUOTES_CONTRACT_V1.md",
        "status": "DEGRADED_PASS" if acceptance_ok else "BLOCKED",
        "release_ready": False,
        "scope": "独立盘中报价能力门、报价时间/单位/映射合同和fail-closed空态",
        "evidence": {
            "registry_dataset_status": dataset["status"],
            "view_path": str(VIEW_PATH),
            "view_sha256": hashlib.sha256(VIEW_PATH.read_bytes()).hexdigest(),
            "capability_status": view["capability_status"],
            "unavailable_reason": view["unavailable_reason"],
            "items": len(view["items"]),
            "network_calls": 0,
            "production_tables_written": False,
            "api39_enabled": False,
            "hot_rank_reused_as_quote": False,
            "local_snapshot_mutated": False,
        },
        "independent_audit_items": [
            {
                "item": "M14-05-QUOTE-SOURCE-AUTHORIZATION",
                "status": "OPEN_GATE",
                "scope": "独立报价来源许可、稳定性和10个交易日观察",
                "acceptance": "完成来源条款、报价时间、单位、映射、缓存及样本证据后才可启用",
            },
            {
                "item": "M14-05-QUOTE-SEMANTICS",
                "status": "OPEN_GATE",
                "scope": "quote_time、source_as_of、价格/金额/成交量单位及quote_state",
                "acceptance": "缺失或未来报价不进入严格视图，未知不填0",
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
        "acceptance": "DEGRADED_PASS: 报价能力独立登记并保持NOT_VERIFIED；未把热榜字段当报价，不启用API39/UI，不产生在线报价批次",
        "next_stage": "M14-06-LH-LIST",
        "next_stage_contract": "先核对低优先龙虎榜来源、交易日/发布时间和来源映射；无稳定来源则明确UNAVAILABLE，不影响本地主流程",
        "next_stage_requires_manual_start": True,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "capability_status": view["capability_status"], "unavailable_reason": view["unavailable_reason"]}, ensure_ascii=False))
    return 0 if acceptance_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
