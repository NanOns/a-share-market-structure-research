"""Bounded metadata-only current probe for V3 P09-01-B-EXT11."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workbench_online.base import FetchResult, OnlineFetchPolicy, bounded_get  # noqa: E402
from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes  # noqa: E402


REGISTRY = ROOT / "config" / "online_source_registry_v3.json"
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
GUARDRAILS = ROOT / "AGENTS.md"
SOURCE_ID = "EXT11"
SECURITY_IDS = ["SH.600000", "SZ.000001"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: object) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _coverage(rows: list[dict], field: str) -> dict:
    present = sum(row.get(field) is not None for row in rows)
    return {"present": present, "total": len(rows), "ratio": present / len(rows) if rows else 0.0}


def build_receipt(result: FetchResult | None, rows: list[dict], *, error: str | None = None) -> dict:
    requested = list(SECURITY_IDS)
    returned_ids = [str(row.get("security_id")) for row in rows if row.get("security_id")]
    unique_returned_ids = sorted(set(returned_ids))
    requested_set = set(requested)
    coverage_ids = sorted(requested_set.intersection(unique_returned_ids))
    schema_valid = bool(rows) and all(
        isinstance(row, dict) and row.get("security_id") in requested_set and all(_finite(row.get(field)) for field in ("price", "ret1", "amount", "volume"))
        for row in rows
    )
    response_ok = result is not None and result.status_code == 200 and "json" in result.content_type.lower()
    current_probe_status = "CURRENT_PROBE_PARSED" if error is None and response_ok and schema_valid else "SOURCE_UNAVAILABLE_OR_SCHEMA_INVALID"
    field_coverage = {field: _coverage(rows, field) for field in ("price", "ret1", "amount", "volume", "turnover_rate", "quote_time")}
    market_coverage = {market: sum(item.startswith(f"{market}.") for item in unique_returned_ids) for market in ("SH", "SZ", "BJ")}
    return {
        "receipt_id": "P09-01-B-EXT11-CURRENT-PROBE-20260913",
        "stage": "P09-01-B-EXT11",
        "source_id": SOURCE_ID,
        "dataset": "LIVE_QUOTES",
        "contract_id": "V3_ONLINE_SOURCE_REGISTRY_1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DEGRADED_PASS" if current_probe_status == "CURRENT_PROBE_PARSED" else "BLOCKED",
        "release_ready": False,
        "probe": {
            "status": current_probe_status,
            "requested_security_ids": requested,
            "returned_security_ids": unique_returned_ids,
            "coverage_security_ids": coverage_ids,
            "coverage_ratio": len(coverage_ids) / len(requested),
            "market_coverage": market_coverage,
            "field_coverage": field_coverage,
            "error": error,
            "response": {
                "status_code": result.status_code if result else None,
                "content_type": result.content_type if result else None,
                "byte_count": result.byte_count if result else None,
                "raw_sha256": result.raw_sha256 if result else None,
                "requested_at_utc": result.requested_at_utc if result else None,
                "received_at_utc": result.received_at_utc if result else None,
            },
        },
        "conversion_evidence": {
            "adapter": "workbench_online.eastmoney_quotes.fetch_eastmoney_quotes",
            "endpoint_template_source": "config/online_source_registry_v3.json:EXT11",
            "response_path": "data.diff",
            "price": "f2 -> price; observed finite values",
            "ret1": "f3 -> percent divided by 100 by existing adapter; exact unit remains subject to repeated-source confirmation",
            "amount": "f6 -> amount; observed finite values, source unit remains subject to confirmation",
            "volume": "f47 -> volume; observed finite values, source unit remains subject to confirmation",
            "turnover": "f168 -> percent divided by 100 by existing adapter; coverage and unit require further confirmation",
            "quote_time": "not supplied by source; do not use f170 or collection time as quote_time",
            "market_mapping": "existing adapter accepts SH/SZ only and returns canonical requested IDs; BJ remains unsupported",
        },
        "capability_decision": {
            "observed_quote": "DEGRADED_AVAILABLE_FOR_DISPLAY_ONLY" if current_probe_status == "CURRENT_PROBE_PARSED" else "UNAVAILABLE",
            "timestamped_rank": "NOT_VERIFIED",
            "reason_codes": ["SOURCE_QUOTE_TIME_MISSING", "UNITS_NEED_REPEATED_CONFIRMATION"] if current_probe_status == "CURRENT_PROBE_PARSED" else ["CURRENT_PROBE_FAILED"],
        },
        "request_policy": {
            "timeout_seconds": 8,
            "max_response_bytes": 2000000,
            "max_security_ids": 50,
            "network_calls": 1 if result is not None or error is not None else 0,
            "credentials_used": False,
            "retries": 0,
        },
        "guardrails": {
            "raw_payload_persisted": False,
            "normalized_rows_persisted": False,
            "hot_rank_or_quote_batch_persisted": False,
            "production_tables_written": False,
            "tdx_inputs_modified": False,
            "future_data_used": False,
            "automated_trading_added": False,
            "probability_claims_added": False,
            "local_core_blocked": False,
        },
        "bound_hashes": {
            "AGENTS.md": sha256(GUARDRAILS),
            "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md": sha256(SPEC),
            "config/online_source_registry_v3.json": sha256(REGISTRY),
        },
        "acceptance": "DEGRADED_PASS: EXT11 当前响应可解析且 2/2 标的返回；仅允许观察性展示，因 quote_time 缺失及单位需重复确认，严格 TIMESTAMPED_RANK 保持 NOT_VERIFIED" if current_probe_status == "CURRENT_PROBE_PARSED" else "BLOCKED: EXT11 当前复测未获得可解析响应；RemoteDisconnected/源端失败按 fail-closed 处理，不能启用在线能力",
        "next_stage": "P09-01-B-EXT01" if current_probe_status == "CURRENT_PROBE_PARSED" else "P09-01-B-EXT11-RETRY",
        "next_stage_contract": "复测 EXT01 同花顺涨停池，固定真实字段参数/顶部路径/倍率/分页和失败降级；不臆造 field 数字代码" if current_probe_status == "CURRENT_PROBE_PARSED" else "人工重新启动 EXT11 单源有界复测；成功才固定单位/时间能力，失败继续保留 NOT_VERIFIED",
        "next_stage_requires_manual_start": True,
    }


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


def run_probe() -> dict:
    policy = OnlineFetchPolicy(timeout_seconds=8, max_response_bytes=2000000, retries=0, cache_ttl_seconds=0, personal_research_only=True)
    try:
        result, rows = fetch_eastmoney_quotes(SECURITY_IDS, policy, fetcher=bounded_get)
    except Exception as exc:  # pragma: no cover - exercised by the live environment
        return build_receipt(None, [], error=f"{type(exc).__name__}:{exc}")
    return build_receipt(result, rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/upgrade_v3/P09-01-B-EXT11_CURRENT_PROBE.json")
    args = parser.parse_args()
    receipt = run_probe()
    atomic_write(args.output, receipt)
    print(json.dumps({"status": receipt["status"], "probe_status": receipt["probe"]["status"], "coverage_ratio": receipt["probe"]["coverage_ratio"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if receipt["status"] in {"FULL_PASS", "DEGRADED_PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
