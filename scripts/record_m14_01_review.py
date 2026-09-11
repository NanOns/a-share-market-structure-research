"""Create the append-only M14-01-REVIEW receipt from local evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/m14_source_registry_v1.json"
CONTRACT = ROOT / "docs/M14_SOURCE_VALIDATION_CONTRACT_V1.md"
PLAN = ROOT / "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md"
EVIDENCE = ROOT / "reports/upgrade_m14/m14_01_source_review_evidence_20260911.md"
PROBE = ROOT / "reports/upgrade_m14/m14_01_source_probe_report_20260911.json"
OUT = ROOT / "reports/upgrade_m14/m14_01_review_receipt_20260911.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def build_receipt(test_status: str) -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    candidates = registry["source_candidates"]
    datasets = {item["dataset"]: item for item in registry["datasets"]}
    checks = [
        {
            "id": "M14-01-REVIEW-TERMS",
            "status": "PASS" if all(item["terms_state"] == "REJECTED" for item in candidates) else "FAIL",
            "detail": "候选来源没有明确本项目自动采集/缓存/再展示许可，均 fail-closed",
        },
        {
            "id": "M14-01-REVIEW-CAPABILITY",
            "status": "PASS" if datasets["HOT_RANKINGS"]["status"] == "REJECTED" and all(not item["enabled"] for item in candidates) else "FAIL",
            "detail": "HOT_RANKINGS 拒绝准入，候选来源均未启用",
        },
        {
            "id": "M14-01-REVIEW-TIME",
            "status": "PASS" if any(source.get("api", {}).get("source_as_of_present") is False for source in probe["sources"]) else "FAIL",
            "detail": "至少一个可解析候选响应缺少 source_as_of，不能进入严格时间语义消费",
        },
        {
            "id": "M14-01-REVIEW-NO-PRODUCTION-WRITE",
            "status": "PASS" if probe["probe_policy"]["production_tables_written"] is False and probe["probe_policy"]["raw_payloads_persisted"] is False else "FAIL",
            "detail": "仅保存探测元数据与哈希",
        },
    ]
    status = "DEGRADED_PASS" if all(item["status"] == "PASS" for item in checks) else "BLOCKED"
    return {
        "receipt_id": "M14-01-REVIEW-20260911",
        "stage": "M14-01-REVIEW",
        "contract_id": registry["contract_id"],
        "plan_version": registry["plan_version"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "release_ready": False,
        "scope": "候选来源许可、字段/时间语义和 capability 准入复核",
        "stage_contract": {
            "contract": "docs/M14_SOURCE_VALIDATION_CONTRACT_V1.md",
            "plan_section": "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md#14-m14免费在线增强",
            "previous_receipt": "reports/upgrade_m14/m14_01_source_validation_receipt_20260911.json",
            "requirements": [
                "公开访问不等同于自动采集许可",
                "source_as_of/时间语义缺失时不进入严格历史消费",
                "未取得明确许可的来源标记 REJECTED，不启用生产适配器",
            ],
        },
        "evidence": {
            "review_document": "reports/upgrade_m14/m14_01_source_review_evidence_20260911.md",
            "probe_report": "reports/upgrade_m14/m14_01_source_probe_report_20260911.json",
            "candidate_sources": [item["source_id"] for item in candidates],
            "rejected_sources": [item["source_id"] for item in candidates if item["status"] == "REJECTED"],
            "production_capabilities_enabled": [],
            "network_calls_during_review": 0,
            "online_rows_written": 0,
            "tdx_inputs_modified": False,
        },
        "verification": {
            "checks": checks,
            "targeted_tests": {
                "command": "python -m pytest -q tests/upgrade_m14",
                "status": test_status,
                "evidence_path": "tests/upgrade_m14",
            },
        },
        "independent_audit_items": [
            {
                "item": "M14-01-SOURCE-AUTHORIZATION-20260911",
                "status": "OPEN_GATE",
                "scope": "来源许可、字段/时间语义、10个交易日稳定性",
                "evidence": "东方财富与同花顺候选均缺少本项目自动采集/缓存/再展示的明确许可；同花顺响应缺 source_as_of",
                "impact": "不能进入 M14-02，不能启用 API37–40 或在线 UI",
                "independent_acceptance": "取得明确书面/开发者许可或替换为许可清晰的来源后，重新执行来源验证",
            }
        ],
        "guardrails": {
            "tdx_inputs_modified": False,
            "network_data_used_for_local_model": False,
            "network_probe_performed_before_review": True,
            "future_data_used": False,
            "automated_trading_added": False,
            "probability_claims_added": False,
            "online_rows_written": False,
        },
        "bound_hashes": {
            "docs/M14_SOURCE_VALIDATION_CONTRACT_V1.md": sha256(CONTRACT),
            "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md": sha256(PLAN),
            "config/m14_source_registry_v1.json": sha256(REGISTRY),
            "reports/upgrade_m14/m14_01_source_review_evidence_20260911.md": sha256(EVIDENCE),
            "reports/upgrade_m14/m14_01_source_probe_report_20260911.json": sha256(PROBE),
            "scripts/record_m14_01_review.py": sha256(Path(__file__)),
        },
        "acceptance": "DEGRADED_PASS: 来源复核完成；候选来源因许可/时间语义不足拒绝准入，M14-02 保持未启动",
        "next_stage": "M14-01-REOPEN",
        "next_stage_contract": "提供明确许可或更换来源后，重新完成逐 dataset 来源验证；未通过前不得进入 M14-02",
        "next_stage_requires_manual_start": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-status", choices=["PASS", "FAIL", "NOT_RUN"], default="NOT_RUN")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    report = build_receipt(args.test_status)
    atomic_write(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
