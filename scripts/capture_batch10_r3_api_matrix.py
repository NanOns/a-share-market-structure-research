"""Capture a read-only 28766 date-context/API matrix for BATCH10-R3 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def request(base: str, route: str, params: dict[str, str]) -> tuple[int, bytes, dict]:
    url = base.rstrip("/") + route + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
        return response.status, raw, json.loads(raw)


def owners(payload: dict) -> dict:
    result = {}
    for domain, binding in (payload.get("dated_owner_bindings") or {}).items():
        path = binding.get("path", "")
        pieces = Path(path).parts
        run_token = next((p for p in pieces if len(p) == 64 and all(c in "0123456789abcdef" for c in p)), None)
        result[domain] = {"run_token": run_token, "sha256": binding.get("sha256"), "path": path}
    return result


def summarize(route: str, day: str, token: str, status_code: int, raw: bytes, payload: dict) -> dict:
    context = payload.get("context") or {}
    return {
        "route": route,
        "query_trade_date": day,
        "http_status": status_code,
        "status": payload.get("status"),
        "code": payload.get("code"),
        "snapshot_context_token": payload.get("snapshot_context_token") or payload.get("context_token"),
        "expected_snapshot_context_token": token,
        "snapshot_context_trade_date": payload.get("snapshot_context_trade_date") or context.get("trade_date"),
        "data_trade_date": payload.get("data_trade_date") or payload.get("trade_date"),
        "total": payload.get("total"),
        "items_returned": len(payload.get("items") or []),
        "item_entity_id": (payload.get("item") or {}).get("entity_id"),
        "period": payload.get("period"),
        "owner_bindings": owners(payload),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
    }


def capture(base: str, token: str, entity_id: str) -> dict:
    evidence = {
        "contract_id": "BATCH10_R3_28766_API_DATE_CONTEXT_MATRIX_R1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "service": base,
        "snapshot_context_token": token,
        "snapshot_context_trade_date": "2026-10-21",
        "entity_id": entity_id,
        "historical_pit_eligible": False,
        "production_accepted": False,
        "checks": [],
    }

    def add(day: str, route: str, params: dict[str, str] | None = None) -> dict:
        query = {"trade_date": day, "context_token": token, **(params or {})}
        code, raw, payload = request(base, route, query)
        row = summarize(route, day, token, code, raw, payload)
        evidence["checks"].append(row)
        return row

    # Cross-day domain reads use one fixed snapshot context; each dated owner
    # binding and payload date must follow the requested historical session.
    for day in ("2026-10-19", "2026-10-20", "2026-10-21"):
        add(day, "/api/v4/context")
        add(day, "/api/v4/stocks", {"limit": "5", "offset": "0"})
        add(day, "/api/v4/sectors", {"limit": "5", "offset": "0"})
        add(day, "/api/v4/focus", {"limit": "5", "offset": "0"})
        add(day, f"/api/v4/stocks/{entity_id}/profile")

    day = "2026-10-20"
    for period in ("D", "W", "M"):
        add(day, f"/api/v4/stocks/{entity_id}/chart", {"period": period, "limit": "5"})
    add(day, "/api/v4/stocks", {"limit": "5", "offset": "30"})
    add(day, "/api/v4/stocks", {"q": "SH.688411", "limit": "5", "offset": "0"})

    # Repeat after switching dates to prove the application cache is keyed by
    # requested data date as well as the fixed snapshot token.
    first = next(x for x in evidence["checks"] if x["route"] == "/api/v4/stocks" and x["query_trade_date"] == day and x.get("total") is not None)
    repeat = add(day, "/api/v4/stocks", {"limit": "5", "offset": "0"})
    evidence["cache_round_trip"] = {
        "sequence": ["2026-10-20", "2026-10-21", "2026-10-20"],
        "first_20_sha256": first["response_sha256"],
        "return_20_sha256": repeat["response_sha256"],
        "byte_identical": first["response_sha256"] == repeat["response_sha256"],
        "final_data_date": repeat["data_trade_date"],
        "final_snapshot_token": repeat["snapshot_context_token"],
    }
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:28766")
    parser.add_argument("--token", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = capture(args.base, args.token, args.entity_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({"output": str(args.output), "check_count": len(data["checks"]),
                      "cache_round_trip": data["cache_round_trip"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
