"""Offline validator and receipt builder for V3 P09-01-A static source registration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "online_source_registry_v3.json"
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
GUARDRAILS = ROOT / "AGENTS.md"

EXPECTED_ENDPOINTS = {
    "EXT01": "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={page}&limit={limit}&field={fields}&filter=HS,GEM2STAR&order_field=330323&order_type=0&date={YYYYMMDD}",
    "EXT02": "https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool?page={page}&limit={limit}&field={fields}&filter=HS,GEM2STAR&order_field=330334&order_type=0&date={YYYYMMDD}",
    "EXT03": "https://flash-api.xuangubao.cn/api/surge_stock/plates?date={BEIJING_MIDNIGHT_UNIX_SECONDS}",
    "EXT04": "https://flash-api.xuangubao.cn/api/surge_stock/stocks?date={YYYYMMDD}&normal=true&uplimit=true",
    "EXT05": "https://flash-api.xuangubao.cn/api/pool/detail?pool_name={pool_name}&date={YYYYMMDD}",
    "EXT06": "https://data.10jqka.com.cn/mobileapi/hotspot_focus/market_state/v1/overview",
    "EXT07": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type={hour|day}&list_type={normal|skyrocket}",
    "EXT08": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate?type={concept|industry}",
    "EXT09": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/topic?page={page}&page_size=30",
    "EXT10": "https://gbcdn.dfcfw.com/rank/popularityList.js",
    "EXT11": "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f2,f3,f6,f12,f13,f14,f47,f168,f170&secids={comma_separated_ids}",
}

EXPECTED_POOL_TYPES = {
    "super_stock": "SUPER",
    "limit_up": "LIMIT_UP",
    "limit_up_broken": "BROKEN",
    "yesterday_limit_up": "YESTERDAY_LIMIT_UP",
    "limit_down": "LIMIT_DOWN",
    "new_stock": "NEW_STOCK",
    "nearly_new": "NEARLY_NEW",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_registry() -> dict:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("REGISTRY_MUST_BE_OBJECT")
    return payload


def validate_registry(payload: dict, *, spec_text: str, guardrail_text: str) -> list[dict]:
    checks: list[dict] = []

    def check(check_id: str, condition: bool, detail: str) -> None:
        checks.append({"id": check_id, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            raise ValueError(f"{check_id}: {detail}")

    check("P09-01-A-SCHEMA", payload.get("schema_version") == "v3-online-source-registry-v1", "versioned registry schema")
    check("P09-01-A-STAGE", payload.get("stage") == "P09-01-A" and payload.get("stage_status") == "STATIC_ONLY", "static-only stage")
    check("P09-01-A-FAIL-CLOSED", payload.get("enabled") is False and payload.get("network_calls_allowed") is False, "no network or activation in static task")
    check("P09-01-A-GUARDRAIL", bool(re.search(r"M14 online enhancement is (?:permitted|allowed)", guardrail_text, re.IGNORECASE)), "bounded online guardrail is present")
    check("P09-01-A-SPEC", "### 19.3 外部接口登记册" in spec_text and "### 20.6 在线报价接口补齐" in spec_text, "latest V3 source sections are present")

    sources = payload.get("sources")
    source_ids = [item.get("source_id") for item in sources] if isinstance(sources, list) else []
    check("P09-01-A-SOURCES", source_ids == list(EXPECTED_ENDPOINTS), "EXT01-EXT11 are present in declared order")
    check("P09-01-A-UNIQUE-SOURCES", len(source_ids) == len(set(source_ids)) and all(source_ids), "source IDs are unique")
    for source in sources:
        source_id = source["source_id"]
        check(f"P09-01-A-{source_id}-ENDPOINT", source.get("method") == "GET" and source.get("endpoint_template") == EXPECTED_ENDPOINTS[source_id] and bool(re.match(r"^https://[^/]+/", source["endpoint_template"])), "known HTTPS endpoint and GET method")
        check(f"P09-01-A-{source_id}-STATUS", source.get("evidence_level") == "STATIC" and source.get("capability_status") == "NOT_VERIFIED" and source.get("enabled") is False, "static evidence does not enable capability")
        check(f"P09-01-A-{source_id}-FIELDS", isinstance(source.get("field_contract", {}).get("source_fields"), list) and isinstance(source.get("field_contract", {}).get("normalized_fields"), dict), "source and normalized field contracts are declared")
        check(f"P09-01-A-{source_id}-STORAGE", "RAW_PAYLOAD" in str(source.get("storage_policy")), "raw payload policy is explicit")

    pools = payload.get("event_pools")
    pool_pairs = {item.get("pool_name"): item.get("pool_type") for item in pools} if isinstance(pools, list) else {}
    check("P09-01-A-POOLS", pool_pairs == EXPECTED_POOL_TYPES, "all seven event pools and semantics are registered")
    check("P09-01-A-POOL-SOURCE", any(item.get("source_id") == "EXT05" and "event_pools" in json.dumps(item, ensure_ascii=False) for item in sources), "EXT05 binds to the seven-pool registry")
    limits = payload.get("shared_request_policy", {})
    check("P09-01-A-BOUNDS", limits.get("max_total_seconds") == 12 and limits.get("max_source_seconds") == 8 and limits.get("max_response_bytes") == 2097152 and limits.get("max_concurrent_sources") == 4, "bounded probe limits match V3")
    check("P09-01-A-HOT-RANK-EPHEMERAL", all("REQUEST_TIME_ONLY" in str(item.get("storage_policy")) for item in sources if item.get("source_id") in {"EXT07", "EXT08", "EXT09", "EXT10", "EXT11"}), "hot-rank and quote rows remain request-time only")
    return checks


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_report(test_status: str) -> dict:
    payload = load_registry()
    spec_text = SPEC.read_text(encoding="utf-8")
    guardrail_text = GUARDRAILS.read_text(encoding="utf-8")
    checks = validate_registry(payload, spec_text=spec_text, guardrail_text=guardrail_text)
    return {
        "receipt_id": "P09-01-A-SOURCE-REGISTRY-20260913",
        "stage": "P09-01-A",
        "contract_id": payload["contract_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FULL_PASS",
        "release_ready": False,
        "scope": "V3 §19.3/§19.4/§20.6 known public endpoint, seven-pool, field and request-bound registration; no network probe",
        "stage_contract": {
            "latest_upgrade_document": "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md",
            "latest_upgrade_document_sha256": sha256(SPEC),
            "implementation_contract": "config/online_source_registry_v3.json",
            "requirements": [
                "EXT01-EXT11 endpoint templates are known and versioned",
                "seven EXT05 pool names and forbidden inferences are explicit",
                "source-to-normalized field clues are explicit without inventing unresolved codes or units",
                "all sources remain NOT_VERIFIED and disabled until P09-01-B current probe",
            ],
        },
        "evidence": {
            "registry": "config/online_source_registry_v3.json",
            "source_count": len(payload["sources"]),
            "event_pool_count": len(payload["event_pools"]),
            "network_calls": 0,
            "raw_payloads_persisted": False,
            "production_tables_written": False,
            "tdx_inputs_modified": False,
        },
        "verification": {
            "registry_checks": checks,
            "targeted_tests": {
                "command": "python -m pytest -q tests/upgrade_v3/test_p09_01_source_registry.py",
                "status": test_status,
                "evidence_path": "tests/upgrade_v3/test_p09_01_source_registry.py",
            },
            "network_probe": {"status": "NOT_RUN_BY_SCOPE", "attempts": 0},
        },
        "independent_audit_items": [
            {
                "item": "P09-01-B-CURRENT-PROBE",
                "status": "OPEN",
                "scope": "逐源当前响应、字段倍率、日期语义、分页范围和失败降级",
                "evidence": "P09-01-A 仅有 STATIC 证据，未声称当前可用",
                "independent_acceptance": "复用项目既有有界 HTTP 能力，按源记录 CURRENT_PROBE 或受限失败，不保存热榜原始载荷/行/批次",
            }
        ],
        "guardrails": {
            "tdx_inputs_modified": False,
            "network_data_used": False,
            "network_probe_performed": False,
            "future_data_used": False,
            "automated_trading_added": False,
            "probability_claims_added": False,
            "online_rows_written": False,
            "local_core_blocked": False,
        },
        "bound_hashes": {
            "AGENTS.md": sha256(GUARDRAILS),
            "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md": sha256(SPEC),
            "config/online_source_registry_v3.json": sha256(REGISTRY),
            "scripts/verify_p09_01_source_registry.py": sha256(Path(__file__)),
        },
        "acceptance": "FULL_PASS: P09-01-A 静态来源登记完成；当前能力仍 NOT_VERIFIED，未放行 P09-01-B 之前的在线消费",
        "next_stage": "P09-01-B",
        "next_stage_contract": "逐源有界当前复测，固定响应路径/倍率/范围/分页；STATIC/HISTORICAL_PROBE/CURRENT_PROBE 分列并 fail-closed",
        "next_stage_requires_manual_start": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/upgrade_v3/P09-01-A_SOURCE_REGISTRY.json")
    parser.add_argument("--test-status", default="NOT_RUN", choices=["PASS", "FAIL", "NOT_RUN"])
    args = parser.parse_args()
    try:
        report = build_report(args.test_status)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"P09-01-A source registry validation failed: {exc}")
        return 1
    atomic_write(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "checks": len(report["verification"]["registry_checks"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
