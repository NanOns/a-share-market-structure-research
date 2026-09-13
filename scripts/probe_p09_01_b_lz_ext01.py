"""Bounded metadata-only current probe for the V3 Longzijue EXT01 source."""

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
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workbench_online.base import FetchResult, OnlineFetchPolicy, bounded_get  # noqa: E402


CONTRACT = ROOT / "config" / "online_source_contract_lz_ext01_v1.json"
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
GUARDRAILS = ROOT / "AGENTS.md"
SOURCE_ID = "EXT01"
ENDPOINT = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
TRADE_DATE = "20260911"
FIELD_CANDIDATES = ["code", "name", "latest", "change_rate", "amount", "order_amount", "currency_value", "turnover_rate", "open_num", "reason_type", "first_limit_up_time", "last_limit_up_time"]
REQUIRED_ROW_FIELDS = {"code", "name", "latest", "change_rate", "amount"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_shape(value: object, *, depth: int = 0) -> dict:
    if isinstance(value, dict):
        keys = sorted(str(key) for key in value)[:80]
        return {"kind": "object", "key_count": len(value), "keys": keys}
    if isinstance(value, list):
        item_keys = []
        for item in value[:3]:
            if isinstance(item, dict):
                item_keys.append(sorted(str(key) for key in item)[:80])
        return {"kind": "array", "length": len(value), "item_key_sets": item_keys}
    if value is None:
        return {"kind": "null"}
    return {"kind": type(value).__name__}


def _list_paths(value: object, path: str = "$", *, depth: int = 0, limit: int = 40) -> list[dict]:
    if depth > 5 or limit <= 0:
        return []
    found: list[dict] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(child, list):
                found.append({"path": child_path, **_json_shape(child)})
            found.extend(_list_paths(child, child_path, depth=depth + 1, limit=limit - len(found)))
            if len(found) >= limit:
                break
    elif isinstance(value, list):
        for index, child in enumerate(value[:3]):
            found.extend(_list_paths(child, f"{path}[{index}]", depth=depth + 1, limit=limit - len(found)))
            if len(found) >= limit:
                break
    return found[:limit]


def _candidate_rows(payload: object) -> tuple[str | None, list[dict]]:
    candidates: list[tuple[str, list[dict]]] = []

    def visit(value: object, path: str = "$", depth: int = 0) -> None:
        if depth > 5:
            return
        if isinstance(value, list):
            rows = [item for item in value if isinstance(item, dict)]
            if rows and REQUIRED_ROW_FIELDS.issubset(rows[0]):
                candidates.append((path, rows))
            for index, child in enumerate(value[:3]):
                visit(child, f"{path}[{index}]", depth + 1)
        elif isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{path}.{key}", depth + 1)

    visit(payload)
    return candidates[0] if candidates else (None, [])


def _finite_fields(rows: list[dict], fields: tuple[str, ...]) -> dict:
    result = {}
    for field in fields:
        valid = 0
        for row in rows:
            value = row.get(field)
            try:
                if value is not None and math.isfinite(float(value)):
                    valid += 1
            except (TypeError, ValueError):
                pass
        result[field] = {"valid": valid, "total": len(rows), "ratio": valid / len(rows) if rows else 0.0}
    return result


def build_receipt(result: FetchResult | None, *, error: str | None = None) -> dict:
    payload = None
    parse_error = error
    if result is not None and error is None:
        try:
            payload = json.loads(result.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            parse_error = f"{type(exc).__name__}:{exc}"
    response_ok = result is not None and result.status_code == 200 and "json" in result.content_type.lower()
    row_path, rows = _candidate_rows(payload) if payload is not None else (None, [])
    valid_rows = bool(rows) and all(REQUIRED_ROW_FIELDS.issubset(row) for row in rows)
    parsed = parse_error is None and response_ok and isinstance(payload, dict)
    probe_status = "CURRENT_PROBE" if parsed else "UNAVAILABLE"
    capability = "DEGRADED" if parsed and valid_rows else "UNAVAILABLE"
    reason_codes = [] if parsed and valid_rows else ["EXT01_CURRENT_RESPONSE_UNAVAILABLE"]
    if parsed and not valid_rows:
        reason_codes = ["EXT01_ROW_PATH_OR_FIELDS_UNRESOLVED"]
    next_stage = "P09-02-EXT01-DATA-LAYER" if parsed and valid_rows else "P09-01-B-LZ-EXT03"
    next_contract = "以 EXT01 当前字段证据建立 EventPoolRow/事件批次读取，先固定分页、单位和失败降级" if parsed and valid_rows else "转验 EXT03/04 选股通题材主链；EXT01 保持受限，不返回 EXT11"
    return {
        "receipt_id": "P09-01-B-LZ-EXT01-CURRENT-PROBE-20260913",
        "stage": "P09-01-B-LZ-EXT01",
        "source_id": SOURCE_ID,
        "contract_id": "V3_LZ_EXT01_LIMIT_UP_1",
        "contract_version": "v3-lz-ext01-limit-up-v1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DEGRADED_PASS" if capability == "DEGRADED" else "UNAVAILABLE",
        "release_ready": False,
        "probe": {
            "status": probe_status,
            "trade_date": TRADE_DATE,
            "request": {"page": 1, "limit": 50, "fields": FIELD_CANDIDATES, "filter": "HS,GEM2STAR", "order_field": "330323", "order_type": 0},
            "request_url": result.url if result is not None else ENDPOINT,
            "response": {"status_code": result.status_code if result else None, "content_type": result.content_type if result else None, "byte_count": result.byte_count if result else None, "raw_sha256": result.raw_sha256 if result else None, "requested_at_utc": result.requested_at_utc if result else None, "received_at_utc": result.received_at_utc if result else None},
            "parse_error": parse_error,
            "top_level_shape": _json_shape(payload) if payload is not None else None,
            "data_shape": _json_shape(payload.get("data")) if isinstance(payload, dict) and "data" in payload else None,
            "list_paths": _list_paths(payload) if payload is not None else [],
            "row_path": row_path,
            "row_count": len(rows),
            "page_coverage": "SINGLE_PAGE_ONLY",
            "complete_pagination": False,
        },
        "normalized_fields": {
            "source_fields": sorted(REQUIRED_ROW_FIELDS),
            "candidate_mapping": {"code": "security_id", "name": "security_name", "latest": "price", "change_rate": "ret1", "amount": "amount"},
            "additional_mapping": {"order_amount": "seal_amount", "currency_value": "float_market_cap", "turnover_rate": "turnover", "open_num": "open_count", "reason_type": "source_reason", "first_limit_up_time": "first_limit_up_time", "last_limit_up_time": "last_limit_up_time"},
            "field_scale_status": "UNRESOLVED_UNTIL_REPEATED_SAMPLE",
            "finite_value_coverage": _finite_fields(rows, ("latest", "change_rate", "amount")) if rows else {},
        },
        "capability": {"status": capability, "reason_codes": reason_codes, "enabled": False, "ui_entry": "/api/v3/limit-up/ladder (not connected by this task)"},
        "persistence": {"raw_payload_persisted": False, "normalized_rows_persisted": False, "metadata_receipt_written": True, "production_tables_written": False, "local_run_identity_changed": False, "tdx_inputs_modified": False},
        "request_policy": {"timeout_seconds": 8, "max_response_bytes": 2000000, "retries": 0, "credentials_used": False, "network_calls": 1 if result is not None or error is not None else 0},
        "guardrails": {"future_data_used": False, "automated_trading_added": False, "probability_claims_added": False, "local_core_blocked": False},
        "bound_hashes": {"AGENTS.md": sha256(GUARDRAILS), "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md": sha256(SPEC), "config/online_source_contract_lz_ext01_v1.json": sha256(CONTRACT)},
        "acceptance": "DEGRADED_PASS: EXT01 当前响应可解析并发现涨停池行结构；仅单页探测，字段倍率/完整分页未固定，UI不放行" if capability == "DEGRADED" else "UNAVAILABLE: EXT01 当前请求未获得可接受的 HTTP/JSON/行结构证据；按 V3 转验下一条独立龙字诀主链",
        "next_stage": next_stage,
        "next_stage_contract": next_contract,
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
    params = {"page": 1, "limit": 50, "field": ",".join(FIELD_CANDIDATES), "filter": "HS,GEM2STAR", "order_field": "330323", "order_type": 0, "date": TRADE_DATE}
    url = ENDPOINT + "?" + urlencode(params)
    policy = OnlineFetchPolicy(timeout_seconds=8, max_response_bytes=2000000, retries=0, personal_research_only=True)
    try:
        result = bounded_get(url, policy)
    except Exception as exc:  # pragma: no cover - exercised by live environment
        return build_receipt(None, error=f"{type(exc).__name__}:{exc}")
    return build_receipt(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/upgrade_v3/P09-01-B-LZ-EXT01_CURRENT_PROBE.json")
    args = parser.parse_args()
    receipt = run_probe()
    atomic_write(args.output, receipt)
    print(json.dumps({"status": receipt["status"], "probe_status": receipt["probe"]["status"], "row_path": receipt["probe"]["row_path"], "row_count": receipt["probe"]["row_count"], "next_stage": receipt["next_stage"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "DEGRADED_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
