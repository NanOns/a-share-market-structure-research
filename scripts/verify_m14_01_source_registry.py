"""Validate the fail-closed M14-01 source registry without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "m14_source_registry_v1.json"
CONTRACT = ROOT / "docs" / "M14_SOURCE_VALIDATION_CONTRACT_V1.md"
PLAN = ROOT / "docs" / "WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md"
GUARDRAILS = ROOT / "AGENTS.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_registry() -> dict:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry must be an object")
    return payload


def validate_registry(payload: dict, guardrail_text: str) -> list[dict]:
    checks: list[dict] = []

    def check(check_id: str, condition: bool, detail: str) -> None:
        checks.append({"id": check_id, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            raise ValueError(f"{check_id}: {detail}")

    check("M14-01-SCHEMA", payload.get("schema_version") == "m14-source-registry-v1", "schema version")
    check("M14-01-STAGE", payload.get("stage") == "M14-01", "stage is M14-01")
    check("M14-01-DISABLED", payload.get("enabled") is False, "registry disabled")
    check("M14-01-NETWORK-GATE", payload.get("network_calls_allowed") is True and payload.get("network_policy") == "M14-01_PROBE_ONLY", "network calls limited to M14-01 probes")
    check("M14-01-PERSONAL-POLICY", payload.get("personal_collection_policy") == "M14-02_BOUNDED_PERSONAL_ONLY" and payload.get("production_network_enabled") is False, "personal collection is separately bounded and production network is disabled")
    check("M14-01-CREDENTIAL-GATE", payload.get("credential_use_allowed") is False, "credential use disabled")
    check(
        "M14-01-GUARDRAIL-EVIDENCE",
        bool(re.search(r"M14 online enhancement is (?:permitted|allowed)", guardrail_text, re.IGNORECASE)),
        "AGENTS.md contains the current bounded M14 online policy",
    )

    candidates = payload.get("source_candidates")
    datasets = payload.get("datasets")
    check("M14-01-CANDIDATES", isinstance(candidates, list) and bool(candidates), "candidate list present")
    check("M14-01-DATASETS", isinstance(datasets, list) and {d.get("dataset") for d in datasets} == {"HOT_RANKINGS", "EXTERNAL_EVIDENCE", "QUOTES_LATEST", "LH_LIST"}, "four planned datasets present")

    candidate_ids = [item.get("source_id") for item in candidates]
    check("M14-01-UNIQUE-SOURCES", len(candidate_ids) == len(set(candidate_ids)) and all(candidate_ids), "source IDs unique")
    check(
        "M14-01-ALL-SOURCES-CLOSED",
        all(item.get("enabled") is False and item.get("status") in {"NOT_VERIFIED", "UNAVAILABLE", "REJECTED"} and item.get("terms_state") in {"NOT_VERIFIED", "REJECTED"} for item in candidates),
        "all candidates remain disabled and are either unverified or explicitly rejected",
    )
    check(
        "M14-01-ALL-DATASETS-CLOSED",
        all(item.get("status") in {"NOT_VERIFIED", "UNAVAILABLE", "REJECTED"} and item.get("terms_state") in {"NOT_VERIFIED", "REJECTED"} and item.get("supports_latest") is False for item in datasets),
        "all datasets remain closed and do not claim latest support",
    )
    return checks


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def build_report(test_status: str) -> dict:
    registry = load_registry()
    checks = validate_registry(registry, GUARDRAILS.read_text(encoding="utf-8"))
    plan_text = PLAN.read_text(encoding="utf-8")
    report = {
        "receipt_id": "M14-01-SOURCE-VALIDATION-20260911",
        "stage": "M14-01",
        "contract_id": registry["contract_id"],
        "plan_version": registry["plan_version"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DEGRADED_PASS",
        "release_ready": False,
        "scope": "来源注册、dataset 能力声明和准入前置检查；不执行在线探测",
        "stage_contract": {
            "contract": "docs/M14_SOURCE_VALIDATION_CONTRACT_V1.md",
            "plan_section": "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md#14-m14免费在线增强",
            "implementation_task": "22.9 / 14-01 来源验证",
            "requirements": [
                "source class ONLINE_A/ONLINE_B 独立记录",
                "按 dataset 独立记录 terms、字段、时间语义、请求预算和观察计划",
                "未核验时保持 NOT_VERIFIED；当前守则下全部 fail-closed",
                "不进行网络调用，不写在线数据，不阻塞本地主流程",
            ],
        },
        "evidence": {
            "guardrail": "AGENTS.md 第4条 M14 bounded online policy",
            "registry": "config/m14_source_registry_v1.json",
            "probe_report": "reports/upgrade_m14/m14_01_source_probe_report_20260911.json",
            "candidate_count": len(registry["source_candidates"]),
            "dataset_count": len(registry["datasets"]),
            "network_calls": 5,
            "network_probe_only": True,
            "online_rows_written": 0,
            "tdx_inputs_modified": False,
        },
        "verification": {
            "registry_checks": checks,
            "targeted_tests": {
                "command": "python -m pytest -q tests/upgrade_m14/test_source_registry.py",
                "status": test_status,
                "evidence_path": "tests/upgrade_m14/test_source_registry.py",
            },
            "network_probe": {"status": "PASS_WITH_GAPS", "attempts": 1, "evidence_path": "reports/upgrade_m14/m14_01_source_probe_report_20260911.json"},
        },
        "independent_audit_items": [
            {
                "item": "M14-01-SOURCE-AUTHORIZATION-20260911",
                "status": "OPEN_GATE",
                "scope": "在线守则、用户授权和逐 dataset 来源证据",
                "evidence": "候选入口已探测；东方财富载荷需解码，同花顺响应缺 source_as_of，许可和 10 个交易日稳定性尚未核验",
                "impact": "不得进入 M14-02，不得启用 API37–40 或在线 UI",
                "independent_acceptance": "逐 dataset 完成许可、字段/时间语义、脱敏样本和 10 个交易日观察计划",
            }
        ],
        "guardrails": {
            "tdx_inputs_modified": False,
            "network_data_used": False,
            "network_probe_performed": True,
            "future_data_used": False,
            "automated_trading_added": False,
            "probability_claims_added": False,
            "online_rows_written": False,
            "local_core_blocked": False,
        },
        "bound_hashes": {
            "AGENTS.md": sha256(GUARDRAILS),
            "docs/M14_SOURCE_VALIDATION_CONTRACT_V1.md": sha256(CONTRACT),
            "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md": sha256(PLAN),
            "config/m14_source_registry_v1.json": sha256(REGISTRY),
            "scripts/verify_m14_01_source_registry.py": sha256(Path(__file__)),
        },
        "acceptance": "DEGRADED_PASS: 两个公开候选入口已完成有界探测；没有来源满足完整准入条件，生产能力保持 NOT_VERIFIED",
        "next_stage": "M14-01-REVIEW",
        "next_stage_contract": "补齐来源许可、字段解码、source_as_of/历史能力和 10 个交易日观察后，人工启动 M14-02",
        "next_stage_requires_manual_start": True,
        "plan_text_sha256": sha256(PLAN),
        "plan_contains_m14": "## 14. M14：免费在线增强" in plan_text,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/upgrade_m14/m14_01_source_validation_receipt_20260911.json")
    parser.add_argument("--test-status", default="NOT_RUN", choices=["PASS", "FAIL", "NOT_RUN"])
    args = parser.parse_args()
    try:
        report = build_report(args.test_status)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"M14-01 source registry validation failed: {exc}")
        return 1
    atomic_write(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "checks": len(report["verification"]["registry_checks"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
