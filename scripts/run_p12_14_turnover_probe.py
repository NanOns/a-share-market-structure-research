from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.turnover_enrichment_v3_3 import (  # noqa: E402
    CONTRACT_ID,
    LocalDailyFingerprint,
    bind_turnover_row,
    select_enrichment_ids,
)
from workbench_online.base import OnlineFetchPolicy  # noqa: E402
from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes  # noqa: E402


ACTIVE = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
LOCAL_DAILY = ROOT / "data/normalized/adjusted_daily.parquet"
CONTRACT = ROOT / "config/p12_14_turnover_source_contract_v1.json"
RECEIPT = ROOT / "reports/p12_14/p12_14_turnover_probe.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    bundle_path = Path(active["bundle_path"])
    results_path = bundle_path / "results.json"
    rows = json.loads(results_path.read_text(encoding="utf-8"))
    identity = active["identity"]
    target_date = identity["trade_date"]
    candidate_ids = select_enrichment_ids(row["security_id"] for row in rows)

    placeholders = ",".join("?" for _ in candidate_ids)
    query = f"""
        select security_id, cast(date as varchar), raw_close, raw_amount, raw_volume
        from read_parquet(?) where cast(date as varchar)=? and security_id in ({placeholders})
    """
    with duckdb.connect() as connection:
        local_rows = connection.execute(query, [str(LOCAL_DAILY), target_date, *candidate_ids]).fetchall()
    local = {
        row[0]: LocalDailyFingerprint(row[0], row[1], float(row[2]), float(row[3]), float(row[4]))
        for row in local_rows
    }

    source_error = None
    source_meta = []
    source_rows: list[dict] = []
    completed_batches = 0
    for start in range(0, len(candidate_ids), 50):
        batch = candidate_ids[start:start + 50]
        try:
            result, rows = fetch_eastmoney_quotes(
                batch,
                OnlineFetchPolicy(timeout_seconds=8, max_response_bytes=200_000, retries=0, cache_ttl_seconds=0),
            )
            completed_batches += 1
            source_rows.extend({**row, "source_identity_sha256": result.raw_sha256} for row in rows)
            source_meta.append({
                "http_status": result.status_code,
                "byte_count": result.byte_count,
                "raw_sha256": result.raw_sha256,
                "observed_at_utc": result.received_at_utc,
                "candidate_count": len(batch),
            })
        except Exception as exc:  # source failure is an accepted fail-closed branch
            source_error = f"{type(exc).__name__}:{exc}"
            break

    source_by_id = {row["security_id"]: row for row in source_rows}
    evidence = []
    for security_id in candidate_ids:
        if security_id not in local:
            evidence.append({
                "contract_id": CONTRACT_ID,
                "security_id": security_id,
                "trade_date": target_date,
                "turnover_rate": None,
                "capability_status": "UNAVAILABLE",
                "reason": "LOCAL_FINGERPRINT_MISSING",
            })
            continue
        evidence.append(bind_turnover_row(source_by_id.get(security_id), local[security_id]))

    counts: dict[str, int] = {}
    for item in evidence:
        status = item["capability_status"]
        counts[status] = counts.get(status, 0) + 1
    acceptance = "FULL_PASS" if counts.get("BOUND") else "DEGRADED_PASS"
    receipt = {
        "stage": "P12-14_OPTIONAL_TURNOVER_SOURCE",
        "stage_contract": CONTRACT_ID,
        "acceptance": acceptance,
        "acceptance_scope": "bounded optional source contract, small candidate probe, and fail-closed date binding",
        "source_capability": "BOUND_FOR_MATCHED_ROWS" if counts.get("BOUND") else "CURRENTLY_UNAVAILABLE",
        "source_error": source_error,
        "identity": identity,
        "request": {
            "candidate_count": len(candidate_ids),
            "planned_batch_count": (len(candidate_ids) + 49) // 50,
            "completed_batch_count": completed_batches,
            "max_batch_size": 50,
            "timeout_seconds": 8,
            "retries": 0,
            "max_response_bytes": 200_000,
        },
        "response": source_meta,
        "capability_counts": counts,
        "evidence": evidence,
        "guardrails": {
            "raw_payload_persisted": False,
            "core_score_or_category_rank_changed": False,
            "local_pipeline_blocked_on_failure": False,
            "historical_backfill_attempted": False,
            "tdx_modified": False,
        },
        "hashes": {
            "source_contract": _sha(CONTRACT),
            "implementation": _sha(ROOT / "src/workbench_analysis/turnover_enrichment_v3_3.py"),
            "adapter": _sha(ROOT / "src/workbench_online/eastmoney_quotes.py"),
            "candidate_results": _sha(results_path),
            "local_daily": _sha(LOCAL_DAILY),
        },
        "next_stage": "P12-14_UI_OR_SHADOW_INTEGRATION_SEPARATE_DECISION",
    }
    _atomic_json(RECEIPT, receipt)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
