"""Fixed-sample, idle warm-read latency evidence for the 28766 candidate UI."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import math
import os
import platform
import subprocess
import time

ROOT = Path(__file__).resolve().parents[4]
BASE = "http://127.0.0.1:28766"
SAMPLES = 50
TIMEOUT_SECONDS = 15


def request(path, params=None):
    url = BASE + path + ("?" + urlencode(params or {}, doseq=True) if params else "")
    started = time.perf_counter()
    try:
        req = Request(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip"})
        with urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            body = json.loads(response.read())
            return response.status, body, round((time.perf_counter() - started) * 1000, 3), None
    except HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except ValueError:
            body = {"error_body": "NON_JSON"}
        return exc.code, body, round((time.perf_counter() - started) * 1000, 3), type(exc).__name__
    except (TimeoutError, URLError, OSError, ValueError) as exc:
        return None, {"error": type(exc).__name__, "message": str(exc)}, round(
            (time.perf_counter() - started) * 1000, 3), type(exc).__name__


def nearest_rank(values, q):
    return sorted(values)[max(0, math.ceil(q * len(values)) - 1)] if values else None


def main():
    context_status, context, context_ms, context_error = request("/api/v4/context")
    if context_status != 200 or context.get("status") != "READY":
        raise SystemExit(f"context is unavailable: {context_status} {context_error} {context}")
    token = context["context_token"]
    day = context["context"]["trade_date"]
    query = {"trade_date": day, "context_token": token}
    routes = {
        "context": ("/api/v4/context", {}),
        "home": ("/api/v4/home", {}),
        "market": ("/api/v4/market", {}),
        "sectors": ("/api/v4/sectors", {"limit": 30, "offset": 0}),
        "stocks": ("/api/v4/stocks", {"limit": 30, "offset": 0}),
        "focus": ("/api/v4/focus", {"limit": 30, "offset": 0}),
        "forward_settlement": ("/api/v4/forward/settlement", {"limit": 30, "offset": 0}),
    }
    result = {
        "contract_id": "BATCH10_R4_E_28766_IDLE_WARM_P95_R1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {"trade_date": day, "context_token": token, "evidence_class": "NON_PIT",
                      "formal_head_modified": False, "production_head_modified": False},
        "endpoint": BASE,
        "server_pid": None,
        "measurement": {"state": "IDLE_NO_DAILY_COMPUTE", "sample_size_per_route": SAMPLES,
                        "max_concurrency": 1, "timeout_seconds": TIMEOUT_SECONDS,
                        "warmup_excluded_from_percentiles": True,
                        "percentile_method": "nearest_rank_ceil_qN"},
        "runtime": {"platform": platform.platform(), "logical_cpu_count": os.cpu_count()},
        "routes": {},
    }
    try:
        import psutil
        result["runtime"]["physical_memory_bytes"] = psutil.virtual_memory().total
    except ImportError:
        result["runtime"]["physical_memory_bytes"] = None
    try:
        result["server_pid"] = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetTCPConnection -State Listen -LocalPort 28766 | Select-Object -First 1 -ExpandProperty OwningProcess)"],
            text=True, timeout=5).strip()
    except Exception:
        result["server_pid"] = "UNAVAILABLE"

    aborted = False
    for name, (path, extra) in routes.items():
        params = {**query, **extra}
        status_code, body, warmup_ms, error = request(path, params)
        record = {"path": path, "warmup_ms": warmup_ms, "warmup_http_status": status_code,
                  "samples_ms": [], "failures": [], "status_counts": {}}
        result["routes"][name] = record
        if status_code != 200 or body.get("status") not in ("READY", "EMPTY_VALID", "SOURCE_INCOMPLETE"):
            record["failures"].append({"kind": "WARMUP_FAILED", "http_status": status_code,
                                       "error": error, "body": body})
            aborted = True
        else:
            for sample in range(SAMPLES):
                status_code, body, elapsed_ms, error = request(path, params)
                record["samples_ms"].append(elapsed_ms)
                record["status_counts"][str(body.get("status"))] = record["status_counts"].get(str(body.get("status")), 0) + 1
                if status_code != 200 or body.get("status") not in ("READY", "EMPTY_VALID", "SOURCE_INCOMPLETE"):
                    record["failures"].append({"sample": sample + 1, "elapsed_ms": elapsed_ms,
                                               "http_status": status_code, "error": error,
                                               "status": body.get("status"), "reason": body.get("reason")})
                    aborted = True
                    break
                if sample % 10 == 9:
                    print(f"{name}: {sample + 1}/{SAMPLES}", flush=True)
        record["n_completed"] = len(record["samples_ms"])
        record["p50_ms"] = nearest_rank(record["samples_ms"], .50)
        record["p95_ms"] = nearest_rank(record["samples_ms"], .95)
        record["max_ms"] = max(record["samples_ms"], default=None)
        record["p95_2s_candidate_budget_pass"] = record["p95_ms"] is not None and record["p95_ms"] <= 2000 and not record["failures"]
        out = ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/R4_E_28766_IDLE_WARM_P95.json"
        result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["disposition"] = "FAIL_SAMPLE" if aborted else "MEASURING"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"saved partial latency evidence: {name}", flush=True)
        if aborted:
            break
    result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    budget_failures=[name for name,item in result["routes"].items()
                     if not item.get("p95_2s_candidate_budget_pass")]
    result["budget_failures"] = budget_failures
    result["disposition"] = ("FAIL_SAMPLE" if aborted else
                             "FAIL_IDLE_WARM_BUDGET" if budget_failures else
                             "PASS_IDLE_WARM_BUDGETS")
    out = ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/R4_E_28766_IDLE_WARM_P95.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "disposition": result["disposition"],
                      "routes": {name: {"n": item["n_completed"], "p50_ms": item["p50_ms"],
                                        "p95_ms": item["p95_ms"], "max_ms": item["max_ms"],
                                        "failures": len(item["failures"])}
                                 for name, item in result["routes"].items()}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
