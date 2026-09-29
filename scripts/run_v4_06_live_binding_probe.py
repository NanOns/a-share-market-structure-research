"""Run a bounded BaoStock-only diagnostic against the accepted V4-05 target."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, RequestBudget, package_metadata
from workbench_analysis.v4_06_supplemental import (
    BoundedHistoryWorker, ScheduledRequest, atomic_json_write, digest_json,
)

TARGET = "2026-09-28"
LOCAL_DAILY = ROOT / "reports/v4_05/staging/V4_05_R3_T0_COORDINATE_DAILY_HISTORY.jsonl.gz"
ACCEPTED_HEAD = ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json"
FACTORS = ROOT / "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz"
POSTGRES_LEDGER = ROOT / "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
LEDGER = ROOT / "reports/v4_baostock/request_ledger.json"
RECEIPT = ROOT / "reports/v4_06/V4_06_LIVE_PROBE_RECEIPT.json"
CHECKPOINT = ROOT / "reports/v4_06/staging/V4_06_LIVE_PROBE_CHECKPOINT_R2.json"
BOARD_SAMPLES = {"SH_MAIN": "SH.600000", "SZ_MAIN": "SZ.000001",
                 "CHINEXT": "SZ.300750", "STAR": "SH.688001"}


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_ledger(path: Path, day: str) -> int:
    if not path.exists():
        return 0
    value = json.loads(path.read_text(encoding="utf-8"))
    return int(value.get("by_shanghai_date", {}).get(day, {}).get("count", 0))


def load_target_identities() -> dict[str, dict]:
    values = {}
    with gzip.open(FACTORS, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("trade_date") == TARGET:
                values[row["source_security_key"]] = row
    selected = {}
    for board, code in BOARD_SAMPLES.items():
        if code in values:
            selected[code] = {**values[code], "board_scope": board}
    if len(selected) < 2:
        raise RuntimeError("ACCEPTED_TARGET_REPRESENTATIVE_IDENTITIES_INSUFFICIENT")
    return selected


def accepted_publication_id(head: dict) -> str:
    ledger_binding = head.get("evidence_bindings", {}).get("postgres_revision_ledger", {})
    if file_sha(POSTGRES_LEDGER) != ledger_binding.get("sha256"):
        raise RuntimeError("ACCEPTED_POSTGRES_LEDGER_HASH_MISMATCH")
    ledger = json.loads(POSTGRES_LEDGER.read_text(encoding="utf-8"))
    if ledger.get("actual_state_head", {}).get("logical_digest") != head["accepted_artifacts"]["core_profile"]["logical_digest"]:
        raise RuntimeError("ACCEPTED_CORE_STATE_DIGEST_MISMATCH")
    value = str(ledger.get("actual_publication_head", {}).get("publication_id", ""))
    if not value:
        raise RuntimeError("ACCEPTED_CORE_PUBLICATION_ID_MISSING")
    return value


def load_local_daily(codes: set[str], start: str, end: str) -> dict[str, dict[str, dict]]:
    lower, upper = int(start.replace("-", "")), int(end.replace("-", ""))
    found: dict[str, dict[str, dict]] = {code: {} for code in codes}
    with gzip.open(LOCAL_DAILY, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            code = row.get("source_security_key")
            day = int(row.get("trade_date", 0))
            if code not in found or not lower <= day <= upper:
                continue
            if not row.get("raw_ohlc") or len(row["raw_ohlc"]) != 4:
                continue
            found[code][str(day)] = {
                "security_id": row["security_id"], "source_security_key": code,
                "trade_date": str(day), "close": float(row["raw_ohlc"][3]),
                "volume": int(row["volume"]), "amount": float(row["amount"]),
                # The accepted local TDX status artifact anchors bar presence;
                # its isST is unknown, so provider status stays cross-check only.
                "tradestatus": "1", "isST": None,
            }
    return found


def select_sample_dates(common_dates: list[str], target: str) -> list[str]:
    if not common_dates:
        return []
    chosen = {target} if target in common_dates else set()
    n = min(5, len(common_dates))
    if n == 1:
        chosen.add(common_dates[-1])
    else:
        for i in range(n):
            chosen.add(common_dates[round(i * (len(common_dates) - 1) / (n - 1))])
    return sorted(chosen)


def summarize_rows(request: ScheduledRequest, rows: list, local_rows: dict[str, dict]) -> dict:
    by_date = {row.trade_date.replace("-", ""): row for row in rows}
    common = sorted(set(by_date) & set(local_rows))
    close_deltas: list[float] = []
    volume_deltas: list[float] = []
    amount_deltas: list[float] = []
    sample_rows = []
    strict_count = 0
    target_status = "MISSING"
    for day in common:
        source = by_date[day]
        local = local_rows[day]
        dc = abs(local["close"] - source.close_price_cny)
        dv = None if source.volume_shares is None else abs(local["volume"] - source.volume_shares)
        da = None if source.amount_cny is None else abs(local["amount"] - source.amount_cny)
        close_deltas.append(dc)
        if dv is not None:
            volume_deltas.append(dv)
        if da is not None:
            amount_deltas.append(da)
    for day in select_sample_dates(common, TARGET.replace("-", "")):
        source = by_date[day]
        local = local_rows[day]
        dc = abs(local["close"] - source.close_price_cny)
        dv = None if source.volume_shares is None else abs(local["volume"] - source.volume_shares)
        da = None if source.amount_cny is None else abs(local["amount"] - source.amount_cny)
        exact = dc == 0 and dv == 0 and da == 0
        status = ("BOUND_SOFT" if exact else "UNBOUND")
        if day == TARGET.replace("-", ""):
            target_status = status
        sample_rows.append({
            "security_id": local["security_id"], "source_security_key": request.provider_code,
            "provider_code": source.source_code, "trade_date": source.trade_date,
            "provider_close_cny": source.close_price_cny, "provider_volume_shares": source.volume_shares,
            "provider_amount_cny": source.amount_cny, "turnover_raw_value": source.turn_source_value,
            "turnover_raw_unit": source.turn_source_unit, "turnover_normalized_fraction": source.turn_fraction,
            "provider_tradestatus": source.tradestatus, "provider_is_st": source.is_st,
            "local_close_cny": local["close"], "local_volume_shares": local["volume"],
            "local_amount_cny": local["amount"], "local_tradestatus": local["tradestatus"],
            "local_is_st": "UNKNOWN", "abs_delta": {"close": dc, "volume": dv, "amount": da},
            "fingerprint_exact": exact, "binding_status": status,
            "quality_codes": (["TOLERANCE_UNFROZEN_DIAGNOSTIC_ONLY", "LOCAL_ISST_UNKNOWN_CROSSCHECK_ONLY"]
                              if exact else ["LOCAL_SOURCE_FINGERPRINT_CONFLICT"]),
            "source_digest": source.source_digest,
        })
    return {
        "security_id": request.security_id, "source_security_key": request.provider_code.upper(),
        "board_scope": next((row["board_scope"] for row in load_target_identities().values()
                              if row["security_id"] == request.security_id), None),
        "provider_code": request.provider_code, "query_row_count": len(rows),
        "local_row_count": len(local_rows), "common_date_count": len(common),
        "target_date_present": TARGET.replace("-", "") in by_date,
        "target_row_status": target_status,
        "max_abs_delta": {"close": max(close_deltas, default=None),
                          "volume": max(volume_deltas, default=None),
                          "amount": max(amount_deltas, default=None)},
        "exact_common_date_count": sum(
            abs(local_rows[day]["close"] - by_date[day].close_price_cny) == 0
            and by_date[day].volume_shares is not None
            and abs(local_rows[day]["volume"] - by_date[day].volume_shares) == 0
            and by_date[day].amount_cny is not None
            and abs(local_rows[day]["amount"] - by_date[day].amount_cny) == 0
            for day in common
        ),
        "sample_rows": sample_rows,
        "source_rows_digest": hashlib.sha256("\n".join(row.source_digest for row in rows).encode()).hexdigest(),
        "local_expected_sample_digest": digest_json([
            {"date": day, "close": local_rows[day]["close"], "volume": local_rows[day]["volume"],
             "amount": local_rows[day]["amount"]} for day in common
        ]),
        "strict_bound_row_count": strict_count,
    }


def main() -> int:
    head = json.loads(ACCEPTED_HEAD.read_text(encoding="utf-8"))
    if head.get("external_acceptance") != "EXTERNALLY_ACCEPTED" or head.get("target_trade_date") != TARGET:
        raise RuntimeError("ACCEPTED_V4_05_TARGET_MISMATCH")
    for name in ("core_profile", "full_scope_factors"):
        artifact = head["accepted_artifacts"][name]
        if file_sha(ROOT / artifact["path"]) != artifact["sha256"]:
            raise RuntimeError(f"ACCEPTED_ARTIFACT_HASH_MISMATCH:{name}")
    publication_id = accepted_publication_id(head)
    identities = load_target_identities()
    start = (date.fromisoformat(TARGET) - timedelta(days=370)).isoformat()
    local = load_local_daily(set(identities), start, TARGET)
    requests = [ScheduledRequest("P1_MISSING_RECENT_WINDOW", row["security_id"], code.lower(), TARGET)
                for code, row in identities.items()]
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    budget_day = RequestBudget._today_shanghai()
    before = count_ledger(LEDGER, budget_day)
    summary_by_code: dict[str, dict] = {}
    client = BaoStockClient(RequestBudget(LEDGER), timeout=30, auth_mode="PUBLIC_ANONYMOUS")
    checkpoint = {}
    failure = None
    started = time.monotonic()

    def on_rows(request: ScheduledRequest, rows: list) -> dict:
        summary = summarize_rows(request, rows, local.get(request.provider_code.upper(), {}))
        summary_by_code[request.provider_code] = summary
        return {"strict_bound_row_count": summary["strict_bound_row_count"],
                "target_row_status": summary["target_row_status"]}

    try:
        with client:
            worker = BoundedHistoryWorker(client, checkpoint_path=CHECKPOINT, max_job_seconds=1_800,
                                          circuit_breaker_failures=2)
            checkpoint = worker.run(requests, start_date=start, end_date=TARGET,
                                    job_id="V4_06_TARGET_2026-09-28_R2", on_rows=on_rows)
    except BaoStockError as exc:
        failure = {"client_error": str(exc), "provider_error_code": exc.provider_code,
                   "provider_error_message": client._safe_message(exc.provider_message)}
    except Exception as exc:
        failure = {"client_error": f"{type(exc).__name__}:{exc}",
                   "provider_error_code": client.login_result.get("error_code")}

    after = count_ledger(LEDGER, budget_day)
    target_rows = [row for row in summary_by_code.values() if row.get("target_date_present")]
    strict_rows = sum(row["strict_bound_row_count"] for row in summary_by_code.values())
    result = {
        "contract_id": "V4_06_BAOSTOCK_TARGET_BINDING_PROBE_V1",
        "status": "LIVE_TARGET_DIAGNOSTIC_ONLY" if target_rows else "LIVE_BINDING_BLOCKED",
        "observed_at_utc": observed_at,
        "target_trade_date": TARGET,
        "accepted_publication_id": publication_id,
        "accepted_core_profile_sha256": head["accepted_artifacts"]["core_profile"]["sha256"],
        "accepted_core_logical_digest": head["accepted_artifacts"]["core_profile"]["logical_digest"],
        "request_range": {"start": start, "end": TARGET, "frequency": "d", "adjustflag": "3"},
        "priority": "P1_MISSING_RECENT_WINDOW",
        "runtime": package_metadata(),
        "endpoint": client.runtime_endpoint,
        "login": client.login_result,
        "logout": client.logout_result,
        "request_count": {"shanghai_date": budget_day, "before": before, "after": after, "delta": after - before},
        "requested_security_count": len(requests),
        "completed_security_count": len(summary_by_code),
        "target_rows_observed": len(target_rows),
        "strict_bound_row_count": strict_rows,
        "binding_policy": "No BOUND_STRICT without independently accepted BaoStock-specific tolerance and denominator semantics.",
        "security_summaries": list(summary_by_code.values()),
        "worker_checkpoint": checkpoint,
        "failure": failure,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "full_provider_payload_persisted": False,
        "minimized_source_sample_fields_persisted": True,
        "credentials_persisted": False,
        "execution_identity": {
            "starting_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": file_sha(Path(__file__)),
            "adapter_sha256": file_sha(ROOT / "src/workbench_analysis/baostock_supplemental.py"),
            "v4_06_module_sha256": file_sha(ROOT / "src/workbench_analysis/v4_06_supplemental.py"),
            "source_contract_sha256": file_sha(ROOT / "config/baostock_supplemental_contract_v1.json"),
        },
        "next_action": "Keep live capability diagnostic-only and route tolerance evidence to independent audit.",
    }
    if not target_rows or strict_rows == 0:
        result["blocker"] = "BAOSTOCK_LIVE_STRICT_BINDING_UNAVAILABLE_OR_UNACCEPTED"
    atomic_json_write(RECEIPT, result)
    print(json.dumps({"status": result["status"], "requested": len(requests),
                      "completed": len(summary_by_code), "target_rows": len(target_rows),
                      "strict_bound": strict_rows, "request_delta": after - before,
                      "failure": failure}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
