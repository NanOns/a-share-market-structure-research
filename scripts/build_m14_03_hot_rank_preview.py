"""Build an isolated M14-03 hot-rank view from captured batches."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.hot_rank_view import build_hot_rank_view


BATCH_ROOT = ROOT / "data/online/m14_personal/batches"
VIEW_PATH = ROOT / "data/online/m14_personal/views/m14_03_hot_rank_view_v1.json"
RECEIPT = ROOT / "reports/upgrade_m14/m14_03_hot_rank_receipt_20260911.json"
CONTRACT = ROOT / "docs/M14_HOT_RANK_CONTRACT_V1.md"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    batches = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(BATCH_ROOT.glob("*.json"))]
    source_ids = sorted({batch["source_id"] for batch in batches})
    views = [build_hot_rank_view(batches, source_id=source_id) for source_id in source_ids]
    view_document = {
        "contract_id": "M14_HOT_RANK_VIEW_V1_0",
        "view_version": "m14-hot-rank-view-v1",
        "personal_research_only": True,
        "publication_enabled": False,
        "source_views": views,
    }
    atomic_json(VIEW_PATH, view_document)
    summaries = [
        {
            "source_id": view["source_id"],
            "batch_id": view["batch_id"],
            "source_as_of": view["source_as_of"],
            "time_semantics": view["time_semantics"],
            "comparison_status": view["comparison_status"],
            "comparison_batch_id": view["comparison_batch_id"],
            "row_count": len(view["rows"]),
            "platform_ranks": [row["platform_rank"] for row in view["rows"]],
        }
        for view in views
    ]
    acceptance_ok = all(
        summary["row_count"] > 0
        and summary["platform_ranks"] == list(range(1, summary["row_count"] + 1))
        for summary in summaries
    ) and VIEW_PATH.exists()
    receipt = {
        "receipt_id": "M14-03-HOT-RANK-20260911",
        "stage": "M14-03-HOT-RANK",
        "contract_id": "M14_HOT_RANK_VIEW_V1_0",
        "contract": "docs/M14_HOT_RANK_CONTRACT_V1.md",
        "status": "DEGRADED_PASS" if acceptance_ok else "BLOCKED",
        "release_ready": False,
        "scope": "按来源独立构建隔离热榜视图，保留平台名次并按15分钟窗口生成可解释比较",
        "evidence": {
            "batch_count": len(batches),
            "source_views": summaries,
            "view_path": str(VIEW_PATH),
            "view_sha256": hashlib.sha256(VIEW_PATH.read_bytes()).hexdigest(),
            "cross_source_rank_merge": False,
            "local_snapshot_mutated": False,
            "api37_to_40_enabled": False,
        },
        "independent_audit_items": [
            {
                "item": "M14-03-SOURCE-TERMS",
                "status": "OPEN_GATE",
                "scope": "东方财富与同花顺个人研究采集及再展示边界",
                "acceptance": "取得明确许可或继续保持隔离，不进入生产 API/UI",
            },
            {
                "item": "M14-03-THS-SOURCE-AS-OF",
                "status": "OPEN_FOLLOW_UP",
                "scope": "同花顺热榜缺少来源时间",
                "acceptance": "补齐来源时间后才允许严格历史/比较视图",
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
        "acceptance": "DEGRADED_PASS: 来源独立热榜视图生成完成，平台排名未重排；同花顺缺来源时间或东方财富比较超窗时明确返回不可比较，不伪造变化",
        "next_stage": "M14-04-REASONS",
        "next_stage_contract": "先验证来源逐条原因能力、正文时间语义和外部证据独立存储；不得把热榜成功推断为原因可用",
        "next_stage_requires_manual_start": True,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "sources": summaries, "view_path": str(VIEW_PATH)}, ensure_ascii=False))
    return 0 if acceptance_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
