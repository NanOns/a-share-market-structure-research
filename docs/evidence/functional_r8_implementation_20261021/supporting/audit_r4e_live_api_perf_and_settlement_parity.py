"""Read-only R4-E HTTP/PG parity and bounded 28766 latency audit."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import statistics
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))


def get_json(path, params=None, timeout=45):
    query = urlencode(params or {}, doseq=True)
    url = f"http://127.0.0.1:28766{path}" + (f"?{query}" if query else "")
    started = time.perf_counter()
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
            return response.status, body, (time.perf_counter() - started) * 1000
    except HTTPError as exc:
        return exc.code, json.loads(exc.read()), (time.perf_counter() - started) * 1000
    except (TimeoutError, URLError, OSError, ValueError) as exc:
        return None, {"error": type(exc).__name__, "message": str(exc)}, (time.perf_counter() - started) * 1000


def percentile(values, q):
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(q * len(ordered)) - 1)], 3)


def main():
    context_status, context, context_ms = get_json("/api/v4/context")
    if context_status != 200 or context.get("status") != "READY":
        raise SystemExit(f"28766 context unavailable: {context_status} {context}")
    token = context["context_token"]
    day = context["context"]["trade_date"]
    dates = [d for d in ("2026-10-19", "2026-10-20", "2026-10-21")
             if d in context["context"].get("available_trade_dates", [])]
    if dates != ["2026-10-19", "2026-10-20", "2026-10-21"]:
        raise SystemExit(f"Expected cross-date candidates unavailable: {dates}")

    route_paths = {
        "home": "/api/v4/home",
        "market": "/api/v4/market",
        "sectors": "/api/v4/sectors",
        "stocks": "/api/v4/stocks",
        "focus": "/api/v4/focus",
        "forward_settlement": "/api/v4/forward/settlement",
    }
    cross_date = []
    for selected_day in dates:
        for domain, path in route_paths.items():
            query = {"trade_date": selected_day, "context_token": token, "limit": 5, "offset": 0}
            status_code, body, elapsed = get_json(path, query)
            valid = status_code == 200 and body.get("data_trade_date", body.get("trade_date", selected_day)) == selected_day
            cross_date.append({"date": selected_day, "domain": domain, "http_status": status_code,
                               "status": body.get("status"), "data_trade_date": body.get("data_trade_date", selected_day),
                               "context_token": body.get("snapshot_context_token", body.get("context_token")),
                               "total": body.get("total"), "elapsed_ms": round(elapsed, 3), "valid": valid,
                               "reason": body.get("reason")})
            if not valid:
                raise SystemExit(f"cross-date route failed: {cross_date[-1]}")
    print("cross-date routes passed:", len(cross_date), flush=True)

    # R4-D's 8/400 sector denominator: enumerate the complete excluded set,
    # requiring an explicit explanation for every non-rankable row.
    priority_common = {"view": "candidate", "trade_date": day, "context_token": token,
                       "scope": "sectors", "limit": 200}
    rankable_status, rankable_page, _ = get_json("/api/v4/radar/priority", dict(priority_common, rankability="RANKABLE", offset=0))
    excluded = []
    excluded_total = None
    for offset in (0, 200):
        status_code, page, _ = get_json("/api/v4/radar/priority", dict(priority_common, rankability="NOT_RANKABLE", offset=offset))
        if status_code != 200 or page.get("status") != "READY":
            raise SystemExit(f"priority exclusion read failed: {status_code} {page}")
        excluded_total = page["total"]
        excluded.extend(page.get("items") or [])
    reasons = Counter()
    unexplained = []
    for row in excluded:
        codes = list(row.get("unknown_inputs") or []) + list(row.get("invalid_inputs") or [])
        if not codes:
            code = row.get("exclusion_reason")
            if code:
                codes = [code]
        if not codes:
            unexplained.append(row.get("entity_id"))
        reasons.update(codes)
        if row.get("rank") is not None or row.get("score") is not None or row.get("priority_state") != "NOT_RANKABLE":
            unexplained.append(row.get("entity_id"))
    excluded_ids = [row.get("entity_id") for row in excluded]
    priority = {"status": rankable_status, "rankable": rankable_page.get("total"),
                "excluded": excluded_total, "denominator": rankable_page.get("rankable_total", 0) + rankable_page.get("not_rankable_total", 0),
                "excluded_rows_returned": len(excluded), "excluded_unique_ids": len(set(excluded_ids)),
                "exclusion_reason_counts": dict(sorted(reasons.items())), "unexplained_or_invalid": unexplained,
                "candidate_only": rankable_page.get("candidate_status") == "CANDIDATE_RECONSTRUCTED"
                                  and rankable_page.get("evidence_class") == "NON_PIT",
                "source_bindings": rankable_page.get("candidate_source_bindings"),
                "rankable_examples": (rankable_page.get("items") or [])[:3],
                "excluded_examples": excluded[:3]}
    if (rankable_status != 200 or priority["rankable"] != 8 or priority["excluded"] != 392
            or priority["denominator"] != 400 or priority["excluded_rows_returned"] != 392
            or priority["excluded_unique_ids"] != 392 or unexplained or not priority["candidate_only"]):
        raise SystemExit(f"Priority denominator/exclusion contract failed: {priority}")
    print("priority exclusion census passed:", priority["rankable"], "/", priority["denominator"], flush=True)

    # Compare filtered HTTP pages to a fresh PG projection through the same
    # production read contract, but on a separate read-only Python process path.
    from workbench_db.forward_r7_store import ForwardR7Store, _configured_forward_dsn
    # Bind to the exact R4 namespace already established by the read-only
    # Forward audit; the repository contains other historical Forward schemas.
    store = ForwardR7Store.__new__(ForwardR7Store)
    store.root = ROOT
    store.dsn = _configured_forward_dsn(ROOT)
    store.schema = "v4_r8_forward_0c2b84fb3e1a0c42"
    store._generic_facts = True
    filter_cases = [
        {},
        {"lane": "historical"},
        {"horizon": 1},
        {"status": "PENDING_FUTURE_SESSION"},
        {"lane": "historical", "horizon": 5, "status": "PENDING_FUTURE_SESSION"},
        {"trade_date": day, "horizon": 1},
        {"trade_date": day, "horizon": 5, "settlement_revision": 1},
    ]
    settlement_parity = []
    for filters in filter_cases:
        params = {"trade_date": day, "context_token": token, "limit": 17, "offset": 19, **filters}
        http_status, body, elapsed = get_json("/api/v4/forward/settlement", params)
        direct = store.read_settlement(
            lane={"historical": "RETROSPECTIVE_RESEARCH", "live": "LIVE_OOS"}.get(filters.get("lane")),
            trade_date=filters.get("trade_date", day), horizon=filters.get("horizon"),
            status=filters.get("status"), limit=17, offset=19,
            revision=filters.get("revision"), settlement_revision=filters.get("settlement_revision"))
        parity = http_status == 200 and body.get("data") == direct and body.get("items") == direct["items"]
        settlement_parity.append({"filters": filters, "http_status": http_status, "http_total": body.get("total"),
                                  "pg_total": direct["total"], "page_count": len(direct["items"]),
                                  "api_equals_fresh_pg_projection": parity, "elapsed_ms": round(elapsed, 3),
                                  "status_counts": direct.get("counts"), "aggregates": direct.get("aggregates")})
        if not parity:
            raise SystemExit(f"settlement filter/PG parity failed: {settlement_parity[-1]}")
    print("settlement / fresh PG parity passed:", len(settlement_parity), flush=True)

    stats_status, stats, _ = get_json("/api/v4/forward/statistics", {"trade_date": day, "context_token": token})
    matured_pg = store.read_matured_count()
    matured_api = (stats.get("data") or {}).get("matured_settlement_count")
    if stats_status != 200 or matured_api != matured_pg:
        raise SystemExit(f"matured Forward count mismatch: api={matured_api} pg={matured_pg}")
    print("matured settlement counter parity passed:", matured_api, flush=True)

    # Warm each API route once, then sample 20 calls per route in bounded waves
    # of four concurrent requests. No writes, mutations, or production traffic.
    performance_routes = {
        "home": ("/api/v4/home", {"trade_date": day, "context_token": token}),
        "market": ("/api/v4/market", {"trade_date": day, "context_token": token}),
        "sectors": ("/api/v4/sectors", {"trade_date": day, "context_token": token, "limit": 30, "offset": 0}),
        "stocks": ("/api/v4/stocks", {"trade_date": day, "context_token": token, "limit": 30, "offset": 0}),
        "focus": ("/api/v4/focus", {"trade_date": day, "context_token": token, "limit": 30, "offset": 0}),
        "forward_settlement": ("/api/v4/forward/settlement", {"trade_date": day, "context_token": token, "limit": 30, "offset": 0}),
    }
    for path, query in performance_routes.values():
        status_code, body, _ = get_json(path, query)
        if status_code != 200 or body.get("status") not in ("READY", "EMPTY_VALID", "SOURCE_INCOMPLETE"):
            raise SystemExit(f"route warm-up failed: {path} {status_code} {body}")
    latency = {name: [] for name in performance_routes}
    failures = Counter()
    sample_size = 20
    with ThreadPoolExecutor(max_workers=4) as pool:
        for wave in range(sample_size):
            for names in (list(performance_routes)[i:i + 4] for i in range(0, len(performance_routes), 4)):
                tasks = [(name, *performance_routes[name]) for name in names]
                futures = [(name, pool.submit(get_json, path, query)) for name, path, query in tasks]
                for name, future in futures:
                    status_code, body, elapsed = future.result(timeout=90)
                    latency[name].append(elapsed)
                    if status_code != 200:
                        failures[name] += 1
            if wave % 5 == 4:
                print("latency sample waves:", wave + 1, "/", sample_size, flush=True)
    perf = {name: {"n": len(values), "p50_ms": percentile(values, .50), "p95_ms": percentile(values, .95),
                   "max_ms": round(max(values), 3), "failures": failures[name]}
            for name, values in latency.items()}
    if any(entry["failures"] for entry in perf.values()):
        raise SystemExit(f"28766 API latency run had failures: {perf}")

    result = {
        "contract_id": "BATCH10_R4_E_LIVE_API_PERF_AND_SETTLEMENT_PARITY_R1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {"trade_date": day, "snapshot_token": token, "available_dates": dates,
                      "evidence_class": "NON_PIT", "production_head_changed": False},
        "database": {"endpoint": "127.0.0.1:5432/market_research", "read_contract": "ForwardR7Store.read_settlement",
                     "fresh_pg_readback": True, "matured_settlement_count_api": matured_api,
                     "matured_settlement_count_pg": matured_pg, "matured_count_equal": matured_api == matured_pg},
        "cross_date_routes": cross_date,
        "priority_400_sector_audit": priority,
        "settlement_filter_parity": settlement_parity,
        "api_latency": {"endpoint": "127.0.0.1:28766", "sample_size_per_route": sample_size,
                         "max_concurrency": 4, "scope": "read_only candidate preview", "routes": perf},
        "limitations": ["No 2026-10-22 source directory exists in the configured TDX dynamic source root; this audit does not fabricate an incremental production date.",
                        "P95 is a bounded dev preview sample, not a sustained production SLO or acceptance test.",
                        "Formal validation cohort and operational Focus-priority Owners are still not bound."]
    }
    out = ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/R4_E_28766_PERF_AND_SETTLEMENT_PARITY.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "dates": len(cross_date), "priority": {
        "rankable": priority["rankable"], "excluded": priority["excluded"],
        "exclusion_reasons": priority["exclusion_reason_counts"]},
        "settlement_parity_cases": len(settlement_parity), "matured_equal": matured_api == matured_pg,
        "p95_ms": {name: value["p95_ms"] for name, value in perf.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
