"""Sep-28 adapter for the accepted V4-04 build_row implementation."""
from __future__ import annotations

from collections import Counter, defaultdict
import gzip
from hashlib import sha256
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.market_regime_ui import RegimeUI
from src.v4.replay_r3_guards import require_factor_visibility

OUT = ROOT / "reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz"
RECEIPT = ROOT / "reports/v4_05/V4_05_R4_CORE_PROFILE_REPLAY.json"
TARGET = "2026-09-28"
CONTRACTS = ("config/v4_04_field_registry_v2.json", "config/v4_04_output_schema_v2.json", "config/v4_04_algorithm_contracts_v3.json", "config/v4_04_parameter_set_v1.json", "config/v4_04_field_window_mapping_v1.json")


def sha(path):
    h = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def date_string(value):
    return f"{value // 10000:04d}-{value // 100 % 100:02d}-{value % 100:02d}"


def groups(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for key, items in itertools.groupby((json.loads(line) for line in stream), key=lambda x: x["source_security_key"]):
            yield key, list(items)


def main():
    accepted = json.loads((ROOT / "data/v4/V4_04_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    for name in CONTRACTS:
        if sha(ROOT / name) != accepted["contract_bindings"][name]["sha256"]:
            raise ValueError(f"accepted V4-04 contract changed: {name}")
    spec = importlib.util.spec_from_file_location("accepted_v4_04_builder", ROOT / "scripts/run_v4_04_full_market_candidate_r4.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.CUTOFF = TARGET
    history = json.loads((ROOT / "reports/v4_05/V4_05_R4_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    period = json.loads((ROOT / "reports/v4_05/V4_05_R4_PERIOD_ASOF.json").read_text(encoding="utf-8"))
    factor = json.loads((ROOT / "reports/v4_05/V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json").read_text(encoding="utf-8"))
    regime = json.loads((ROOT / "reports/v4_05/V4_05_R4_MARKET_REGIME.json").read_text(encoding="utf-8"))
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R4_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    calendars = {market: json.loads((ROOT / calendar_receipt["calendar_bindings"][market]["path"]).read_text(encoding="utf-8"))["session_dates"] for market in ("SSE", "SZSE")}
    regime_ui = RegimeUI("UNKNOWN", "UNKNOWN", None, 0, regime["regime_ui"]["evidence"], regime["regime_ui"]["unknown_reason"])
    contract_digest = builder.digest({name: sha(ROOT / name) for name in CONTRACTS})
    source_digest = builder.digest({"daily": history["artifact_sha256"], "period": period["artifact_sha256"], "factor": factor["artifact_sha256"], "regime": sha(ROOT / "reports/v4_05/V4_05_R4_MARKET_REGIME.json"), "calendar": calendar_receipt["calendar_bindings"]})
    suspended = defaultdict(set)
    with gzip.open(ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            if item["status"] == "SUSPENDED":
                suspended[item["security_id"]].add(item["trade_date"])
    factor_rows = {row["source_security_key"]: row for _, group in groups(ROOT / factor["artifact_path"]) for row in group}
    periods = groups(ROOT / period["artifact_path"])
    boards, quality, unknown, state_unknown = Counter(), Counter(), Counter(), Counter()
    logical = sha256()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    with tmp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as zipped:
        for key, daily in groups(ROOT / history["artifact_path"]):
            period_key, period_rows = next(periods)
            if key != period_key or key not in factor_rows:
                raise ValueError(f"profile input identity mismatch: {key}, {period_key}")
            f = factor_rows[key]
            sid = f["security_id"]
            formal = daily[0]["formal_publication_at"]
            require_factor_visibility(f["fields"], formal)
            market = "SSE" if f["board_scope"] in ("SH_MAIN", "STAR") else "SZSE"
            bars = [{"source_security_key": key, "board_scope": f["board_scope"], "trade_date": date_string(row["trade_date"]),
                     "qfq_close": float(row["qfq_ohlc"][3]) if row["qfq_ohlc"] else None,
                     "qfq_high": float(row["qfq_ohlc"][1]) if row["qfq_ohlc"] else None,
                     "qfq_low": float(row["qfq_ohlc"][2]) if row["qfq_ohlc"] else None,
                     "amount": row["amount"], "adjusted_quality": row["adjusted_quality"]} for row in daily]
            actual = {x["trade_date"] for x in bars}
            first = bars[max(0, len(bars) - 250)]["trade_date"]
            statuses = [(day, "ACTUAL_TRADED" if day in actual else "SUSPENDED" if day in suspended[sid] and day < TARGET else "UNKNOWN")
                        for day in calendars[market] if first <= day <= TARGET]
            period_inputs = {}
            for kind in ("WEEKLY", "MONTHLY"):
                period_inputs[kind] = [{"period_last_session": row["period_last_session"], "period_view": row["period_view"],
                                        "period_status": row["period_status"], "price_basis": "QFQ",
                                        "close": float(row["ohlc"][3]) if row["ohlc"] else None, "source_daily_digest": row["source_daily_digest"]}
                                       for row in period_rows if row["period_type"] == kind and row["price_basis"] == "QFQ"]
            payload = builder.build_row(f, bars, period_inputs["WEEKLY"], period_inputs["MONTHLY"], statuses,
                                        {"source_security_key": key}, source_digest, contract_digest, calendars[market], regime_ui)
            payload.update({"publication_id": "V4_05_R4_T0_CURRENT_COORDINATE", "coordinate_basis": "T0_CURRENT_COORDINATE",
                            "historical_as_recorded_claim": False, "formal_publication_at": daily[0]["formal_publication_at"],
                            "max_source_trade_date": 20260928, "evidence_origin": "V4_05_R4_REPLAY_ONLY"})
            payload["output_digest"] = builder.digest({k: v for k, v in payload.items() if k != "output_digest"})
            line = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            zipped.write(line)
            logical.update(line)
            boards[f["board_scope"]] += 1
            quality[payload["profile_quality"]] += 1
            if daily[-1]["adjusted_quality"] != "READY":
                unknown["upstream_adjusted_unavailable"] += 1
            for field, state in payload["states"].items():
                if state["unknown_reason"]:
                    state_unknown[f"{field}:{state['unknown_reason']}"] += 1
    os.replace(tmp, OUT)
    if sum(boards.values()) != 5222 or unknown["upstream_adjusted_unavailable"] != 27:
        raise ValueError("profile row set/unknown propagation mismatch")
    receipt = {"contract_id": "V4_05_R4_CORE_PROFILE_REPLAY_V1", "status": "DEGRADED_PASS_FIELD_LOCAL_UNKNOWN",
               "artifact_path": OUT.relative_to(ROOT).as_posix(), "artifact_sha256": sha(OUT), "logical_digest": logical.hexdigest(),
               "row_count": sum(boards.values()), "board_counts": dict(boards), "quality_counts": dict(quality),
               "upstream_adjusted_unavailable_entities": unknown["upstream_adjusted_unavailable"], "state_unknown_reasons": dict(state_unknown),
               "source_digest": source_digest, "contract_digest": contract_digest, "accepted_contracts": {name: sha(ROOT / name) for name in CONTRACTS},
               "max_source_trade_date": 20260928, "formal_publication_at": daily[0]["formal_publication_at"], "historical_as_recorded_claim": False}
    temp = RECEIPT.with_suffix(".tmp")
    temp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(temp, RECEIPT)
    print(json.dumps({"rows": receipt["row_count"], "quality": dict(quality), "sha256": receipt["artifact_sha256"]}))


if __name__ == "__main__":
    main()
