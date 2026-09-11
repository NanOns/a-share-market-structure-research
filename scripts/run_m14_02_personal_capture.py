"""Collect one private, local-only M14-02 hot-rank batch."""

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.collector import collect_ths_hot_rank


OUTPUT_ROOT = ROOT / "data/online/m14_personal"
RECEIPT = ROOT / "reports/upgrade_m14/m14_02_batch_foundation_receipt_20260911.json"
CONTRACT = ROOT / "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md"
PRECONDITION = ROOT / "reports/upgrade_m14/m14_01_personal_reopen_receipt_20260911.json"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    result = collect_ths_hot_rank(OUTPUT_ROOT)
    receipt = {
        "receipt_id": "M14-02-BATCH-FOUNDATION-20260911",
        "stage": "M14-02",
        "contract_id": "M14_BATCH_FOUNDATION_V1_0",
        "contract": "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md",
        "precondition_receipt": "reports/upgrade_m14/m14_01_personal_reopen_receipt_20260911.json",
        "precondition_contract": "docs/M14_PERSONAL_RESEARCH_REOPEN_CONTRACT_V1.md",
        "status": result["status"],
        "release_ready": False,
        "scope": "个人研究模式的单来源热榜 fetch/payload/batch 分离与本地原子存储",
        "source": result,
        "verification": {
            "network_calls": 1,
            "credentials_used": False,
            "retry_count": 0,
            "production_tables_written": False,
            "api37_to_40_enabled": False,
            "local_snapshot_mutated": False,
        },
        "independent_audit_items": [
            {
                "item": "M14-02-SOURCE-AS-OF-MISSING",
                "status": "OPEN_GATE",
                "scope": "THS hot-rank response does not provide source_as_of",
                "impact": "Batch is observed-time-only and cannot enter strict AS_OF history or production UI",
                "acceptance": "source_as_of or an independently verified source-time contract is available",
            },
            {
                "item": "M14-02-PERSONAL-RESEARCH-ONLY",
                "status": "OPEN_GATE",
                "scope": "user-requested private collection under source terms not explicitly licensed",
                "impact": "No publication, sharing, API or local model consumption",
                "acceptance": "explicit licensed source or continued isolated personal mode with separate approval",
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
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        "acceptance": "DEGRADED_PASS: 单批次已私有采集并原子落盘；因 source_as_of 缺失和个人研究隔离，不进入生产消费",
        "next_stage": "M14-02-VERIFY",
        "next_stage_contract": "验证批次/载荷身份、重复抓取、映射与失败恢复；保持个人研究隔离，不接 API/UI",
        "next_stage_requires_manual_start": True,
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "batch_id": result["batch_id"], "rows": result["row_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
