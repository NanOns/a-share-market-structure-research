from __future__ import annotations

"""Bounded public route B1 interface probe for the isolated 0.9.3 regression venv."""

import argparse
import hashlib
import importlib.metadata
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import RequestBudget, _atomic_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version", default="0.9.3")
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--start", default="2026-09-01")
    parser.add_argument("--end", default="2026-09-07")
    parser.add_argument("--metadata-day", default="2026-09-07")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--b0-receipt", default="reports/v4_baostock/public_b0_093_regression_receipt.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/public_b1_093_regression_receipt.json")
    args = parser.parse_args()

    b0_path = ROOT / args.b0_receipt
    b0 = json.loads(b0_path.read_text(encoding="utf-8"))
    if b0.get("status") != "PUBLIC_ROUTE_B0_093_PASS":
        raise SystemExit("B1_NOT_RUN_B0_GATE_NOT_PASSED")

    import baostock as bs
    import baostock.common.contants as constants
    import baostock.common.context as context

    version = importlib.metadata.version("baostock")
    if version != args.expected_version:
        raise SystemExit("ISOLATED_SDK_VERSION_MISMATCH")
    if hasattr(context, "apiKey"):
        delattr(context, "apiKey")

    budget = RequestBudget(ROOT / args.ledger)
    prior_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(30)
    started = time.monotonic()
    login = {"error_code": "NOT_ATTEMPTED", "error_msg": ""}
    logout = {"error_code": "NOT_ATTEMPTED", "error_msg": ""}
    endpoint = {"auth_mode": "PUBLIC_ANONYMOUS", "configured_host": constants.BAOSTOCK_SERVER_IP,
                "configured_port": int(constants.BAOSTOCK_SERVER_PORT), "connected_peer_ip": None,
                "connected_peer_port": None}
    results: dict[str, dict] = {}
    failures: dict[str, str] = {}
    rows_by_query: dict[str, list[dict[str, str]]] = {}
    logged_in = False

    def collect(name: str, operation: str, query, row_limit: int, page_limit: int) -> None:
        budget.consume(operation)
        result = query()
        code = str(getattr(result, "error_code", "UNKNOWN"))
        message = str(getattr(result, "error_msg", "") or "")[:500]
        fields = list(getattr(result, "fields", []))
        rows: list[dict[str, str]] = []
        pages = 1
        if code == "0":
            while True:
                data = getattr(result, "data", [])
                current = int(getattr(result, "cur_row_num", 0))
                page_count = int(getattr(result, "per_page_count", -1))
                if current > 0 and current >= len(data) and len(data) == page_count:
                    if pages >= page_limit:
                        raise RuntimeError("B1_PAGE_BOUND_EXCEEDED")
                    budget.consume(operation + "_page")
                    pages += 1
                if not result.next():
                    break
                rows.append(dict(zip(fields, result.get_row_data(), strict=True)))
                if len(rows) > row_limit:
                    raise RuntimeError("B1_ROW_BOUND_EXCEEDED")
                code = str(getattr(result, "error_code", code))
                message = str(getattr(result, "error_msg", message) or "")[:500]
                if code != "0":
                    break
            code = str(getattr(result, "error_code", code))
            message = str(getattr(result, "error_msg", message) or "")[:500]
        results[name] = {"error_code": code, "error_msg": message, "fields": fields,
                         "page_count": pages, "row_count": len(rows)}
        rows_by_query[name] = rows

    try:
        budget.consume("login")
        result = bs.login()
        login = {"error_code": str(getattr(result, "error_code", "UNKNOWN")),
                 "error_msg": str(getattr(result, "error_msg", "") or "")[:500]}
        sock = getattr(context, "default_socket", None)
        if sock is not None:
            peer = sock.getpeername()
            endpoint["connected_peer_ip"], endpoint["connected_peer_port"] = peer[0], peer[1]
            sock.settimeout(30)
        if login["error_code"] == "0":
            logged_in = True
            probes = [
                ("stock_basic", "query_stock_basic", lambda: bs.query_stock_basic(code="sh.600000"), 5, 1),
                ("trade_dates", "query_trade_dates", lambda: bs.query_trade_dates(start_date=args.start, end_date=args.end), 40, 1),
                ("all_stock", "query_all_stock", lambda: bs.query_all_stock(day=args.metadata_day), 10_000, 10),
            ]
            for name, operation, query, row_limit, page_limit in probes:
                try:
                    collect(name, operation, query, row_limit, page_limit)
                except Exception as exc:
                    failures[name] = type(exc).__name__ + ":" + str(exc)[:200]
                    results.setdefault(name, {"error_code": "CLIENT_ERROR", "error_msg": str(exc)[:500],
                                              "fields": [], "page_count": 0, "row_count": 0})
                    rows_by_query.setdefault(name, [])
    except Exception as exc:
        failures["session"] = type(exc).__name__ + ":" + str(exc)[:200]
    finally:
        try:
            if logged_in:
                budget.consume("logout", bypass_soft_stop=True)
                result = bs.logout()
                logout = {"error_code": str(getattr(result, "error_code", "UNKNOWN")),
                          "error_msg": str(getattr(result, "error_msg", "") or "")[:500]}
        except Exception as exc:
            logout = {"error_code": "CLIENT_ERROR", "error_msg": type(exc).__name__}
        finally:
            socket.setdefaulttimeout(prior_timeout)
            sock = getattr(context, "default_socket", None)
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    row_digests = {
        name: hashlib.sha256("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                                 separators=(",", ":")) for row in rows).encode("utf-8")).hexdigest()
        for name, rows in rows_by_query.items()
    }
    counts = {name: len(rows) for name, rows in rows_by_query.items()}
    expected = {"stock_basic", "trade_dates", "all_stock"}
    passed = (login["error_code"] == "0" and expected.issubset(results)
              and all(results[name]["error_code"] == "0" and counts.get(name, 0) > 0 for name in expected))
    ledger_doc = json.loads((ROOT / args.ledger).read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    payload = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-ROUTE-B1-0.9.3-REGRESSION",
        "contract_id": "BAOSTOCK_PUBLIC_RUNTIME_ROUTE_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "api_key_setter_called": False,
        "user_credentials_passed": False,
        "runtime": {"python": sys.version.split()[0], "package": "baostock", "version": version},
        "endpoint": endpoint,
        "login": login,
        "logout": logout,
        "queries": results,
        "failures": failures,
        "row_counts": counts,
        "row_digests": row_digests,
        "request_counts_for_shanghai_day": ledger_doc.get("by_shanghai_date", {}).get(today, {}),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
            "wheel_sha256": hashlib.sha256(Path(args.wheel).read_bytes()).hexdigest(),
            "b0_receipt_sha256": hashlib.sha256(b0_path.read_bytes()).hexdigest(),
        },
        "raw_payload_persisted": False,
        "status": "PUBLIC_CAPABILITY_B1_093_PASS" if passed else "PUBLIC_CAPABILITY_B1_093_BLOCKED",
    }
    _atomic_json(ROOT / args.receipt, payload)
    print(json.dumps({"status": payload["status"], "login": login["error_code"],
                      "row_counts": counts, "query_codes": {key: value["error_code"] for key, value in results.items()},
                      "endpoint": endpoint}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
