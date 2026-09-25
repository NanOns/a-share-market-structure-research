from __future__ import annotations

"""B0 anonymous Quick Start route probe for an isolated BaoStock 0.9.3 venv."""

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
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/public_b0_093_regression_receipt.json")
    args = parser.parse_args()

    import baostock as bs
    import baostock.common.contants as constants
    import baostock.common.context as context

    version = importlib.metadata.version("baostock")
    if version != args.expected_version:
        raise SystemExit("ISOLATED_SDK_VERSION_MISMATCH")
    if hasattr(context, "apiKey"):
        delattr(context, "apiKey")
    ledger = RequestBudget(ROOT / args.ledger)
    prior_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(30)
    started = time.monotonic()
    login = {"error_code": "NOT_ATTEMPTED", "error_msg": ""}
    history = {"error_code": "NOT_ATTEMPTED", "error_msg": "", "fields": [], "row_count": 0,
               "first_date": None, "last_date": None}
    logout = {"error_code": "NOT_ATTEMPTED", "error_msg": ""}
    endpoint = {"auth_mode": "PUBLIC_ANONYMOUS", "configured_host": constants.BAOSTOCK_SERVER_IP,
                "configured_port": int(constants.BAOSTOCK_SERVER_PORT), "connected_peer_ip": None,
                "connected_peer_port": None}
    row_digests: list[str] = []
    failure = None
    logged_in = False
    try:
        ledger.consume("login")
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
            ledger.consume("query_history_k_data_plus_adjustflag_3")
            result = bs.query_history_k_data_plus(
                "sh.600000", "date,code,close,volume,amount,turn,tradestatus,isST",
                start_date=args.start, end_date=args.end, frequency="d", adjustflag="3",
            )
            history["error_code"] = str(getattr(result, "error_code", "UNKNOWN"))
            history["error_msg"] = str(getattr(result, "error_msg", "") or "")[:500]
            history["fields"] = list(getattr(result, "fields", []))
            dates = []
            if history["error_code"] == "0":
                while result.next():
                    row = result.get_row_data()
                    dates.append(str(row[0]))
                    row_digests.append(hashlib.sha256(json.dumps(row, ensure_ascii=False,
                                                                 separators=(",", ":")).encode("utf-8")).hexdigest())
                    if len(dates) > 100:
                        failure = "B0_ROW_BOUND_EXCEEDED"
                        break
            history["row_count"] = len(dates)
            history["first_date"] = min(dates) if dates else None
            history["last_date"] = max(dates) if dates else None
    except Exception as exc:
        failure = type(exc).__name__
        if login["error_code"] == "0":
            history["error_msg"] = str(exc)[:500]
    finally:
        try:
            if logged_in:
                ledger.consume("logout", bypass_soft_stop=True)
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

    passed = login["error_code"] == "0" and history["error_code"] == "0" and history["row_count"] > 0
    ledger_doc = json.loads((ROOT / args.ledger).read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    payload = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-ROUTE-B0-0.9.3-REGRESSION",
        "contract_id": "BAOSTOCK_PUBLIC_RUNTIME_ROUTE_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "api_key_setter_called": False,
        "user_credentials_passed": False,
        "runtime": {"python": sys.version.split()[0], "package": "baostock", "version": version},
        "endpoint": endpoint,
        "login": login,
        "history": history,
        "rows_digest": hashlib.sha256("\n".join(row_digests).encode("ascii")).hexdigest(),
        "logout": logout,
        "request_counts_for_shanghai_day": ledger_doc.get("by_shanghai_date", {}).get(today, {}),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "failure": failure,
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
            "wheel_sha256": hashlib.sha256(Path(args.wheel).read_bytes()).hexdigest(),
        },
        "raw_payload_persisted": False,
        "status": "PUBLIC_ROUTE_B0_093_PASS" if passed else "PUBLIC_ROUTE_B0_093_BLOCKED",
    }
    _atomic_json(ROOT / args.receipt, payload)
    print(json.dumps({"status": payload["status"], "login": login["error_code"],
                      "history": history["error_code"], "row_count": history["row_count"],
                      "endpoint": endpoint}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
