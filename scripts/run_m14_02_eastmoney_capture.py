"""Collect one private Eastmoney hot-rank page after AES payload verification."""

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.collector import collect_eastmoney_hot_rank


OUTPUT_ROOT = ROOT / "data/online/m14_personal"
RECEIPT = ROOT / "reports/upgrade_m14/m14_02_eastmoney_verify_receipt_20260911.json"
CONTRACT = ROOT / "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    result = collect_eastmoney_hot_rank(OUTPUT_ROOT)
    receipt = {
        "receipt_id": "M14-02-VERIFY-EASTMONEY-20260911",
        "stage": "M14-02-VERIFY",
        "contract_id": "M14_BATCH_FOUNDATION_V1_0",
        "contract": "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md",
        "status": result["status"],
        "release_ready": False,
        "scope": "东方财富 AES-CBC 编码热榜载荷解码、字段/时间校验和个人批次落盘",
        "source": result,
        "verification": {
            "network_calls": 1,
            "credentials_used": False,
            "retry_count": 0,
            "decoder_version": result["decoder_version"],
            "source_as_of_verified": result["source_as_of"] is not None,
            "production_tables_written": False,
            "api37_to_40_enabled": False,
            "local_snapshot_mutated": False,
        },
        "independent_audit_items": [
            {
                "item": "M14-02-EASTMONEY-TERMS",
                "status": "OPEN_GATE",
                "scope": "个人研究采集与来源服务协议的边界",
                "impact": "仅个人隔离对象，不进入发布/API/UI",
                "acceptance": "明确许可或保持个人研究隔离并由用户单独承担使用边界",
            },
            {
                "item": "M14-02-EASTMONEY-NAME",
                "status": "OPEN_FOLLOW_UP",
                "scope": "热榜载荷没有股票名称，仅提供代码和平台排名",
                "impact": "当前批次 security_name=NULL，不在适配器内补名或模糊匹配",
                "acceptance": "后续独立、可追溯的本地证券主数据映射，不改变平台名次",
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
        "acceptance": "DEGRADED_PASS: 东方财富编码载荷已解码并完成平台排名/来源时间校验；仍为个人研究隔离批次，不进入生产消费",
        "next_stage": "M14-02-VERIFY-REPLAY",
        "next_stage_contract": "验证重复页抓取、同批次身份、页码/排序稳定性和失败恢复；继续禁止 API/UI 消费",
        "next_stage_requires_manual_start": True,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "batch_id": result["batch_id"], "rows": result["row_count"], "source_as_of": result["source_as_of"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
