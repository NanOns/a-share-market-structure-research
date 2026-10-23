import gzip
import hashlib
import json
from pathlib import Path

from workbench_analysis import r6_candidate_market_stress as stress


def _bind(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = payload if isinstance(payload, bytes) else json.dumps(payload, sort_keys=True).encode()
    path.write_bytes(raw)
    return {"path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _dated_candidate(root, *, include_exact_receipt):
    day = "2026-03-03"
    owner_id = "synthetic-owner"
    base = f"data/v4/dynamic_daily_owners/{day}/{owner_id}"
    freeze = _bind(root, f"{base}/source_freeze.json", {"target_session": day})
    generation = _bind(root, f"{base}/GENERATION_SCOPE.json",
                       {"source_freeze": freeze["sha256"]})
    raw = _bind(root, f"{base}/owner_v3/owners/{day}/raw.jsonl.gz", b"synthetic-raw")
    limit = _bind(root, f"{base}/owner_v3/owners/{day}/daily_price_limits_v1.jsonl.gz",
                  b"synthetic-limits")
    source = _bind(root, f"{base}/sources/{day}/daily_update.json",
                   {"observed_at": f"{day}T16:00:00+08:00", "rows": []})
    contract = _bind(root, "config/limit_contract.json", {"contract_id": "SYN-LIMIT"})
    market = _bind(root, f"{base}/owner_v3/owners/{day}/market.json",
                   {"trade_date": day, "input_bindings": [limit]})
    owner_row = {"trade_date": day, "artifact": limit, "raw_binding": raw,
                 "baostock_source": {**source, "trade_date": day,
                     "candidate_owner_id": owner_id,
                     "capture_observed_at": f"{day}T16:00:00+08:00"},
                 "counts": {"rows": 0}}
    exact_receipt = Path(root / limit["path"]).parents[2] / "DAILY_PRICE_LIMIT_REPLAY.json"
    if include_exact_receipt:
        exact_receipt.parent.mkdir(parents=True, exist_ok=True)
        exact_receipt.write_text(json.dumps({"production_admission": False,
            "contract": contract, "owners": [owner_row]}), encoding="utf-8")
    candidate = {"accepted_trade_date": day, "published_sessions": [day],
        "owners": {day: {"raw": raw, "market": market}},
        "source_registry": {day: {"generation": generation, "freeze": freeze}}}
    return day, candidate, exact_receipt


def test_exact_dated_limit_receipt_skips_global_legacy_scan(tmp_path, monkeypatch):
    day, candidate, receipt_path = _dated_candidate(tmp_path, include_exact_receipt=True)

    def unexpected_glob(self, pattern):
        raise AssertionError(f"historical materialization scan should be skipped: {pattern}")

    monkeypatch.setattr(Path, "glob", unexpected_glob)
    artifact, row, selected_receipt, receipt_sha = stress._limit_owner(tmp_path, candidate, day)

    assert artifact["path"].endswith("daily_price_limits_v1.jsonl.gz")
    assert row["trade_date"] == day
    assert selected_receipt == receipt_path
    assert len(receipt_sha) == 64


def test_legacy_limit_receipt_lookup_remains_available_when_exact_receipt_is_absent(tmp_path):
    day, candidate, exact_receipt = _dated_candidate(tmp_path, include_exact_receipt=False)
    assert not exact_receipt.exists()
    legacy = tmp_path / "r5_daily_limit_materialization_synthetic" / day / "DAILY_PRICE_LIMIT_REPLAY.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    # Reuse the exact synthetic receipt row from a temporary receipt built from
    # the candidate bindings; this exercises only the explicit compatibility path.
    owner = candidate["owners"][day]
    market = json.loads((tmp_path / owner["market"]["path"]).read_bytes())
    limit = market["input_bindings"][0]
    owner_id = candidate["source_registry"][day]["generation"]["path"].split("/")[-2]
    source_path = tmp_path / f"data/v4/dynamic_daily_owners/{day}/{owner_id}/sources/{day}/daily_update.json"
    source = {"path": source_path.relative_to(tmp_path).as_posix(),
              "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
              "bytes": source_path.stat().st_size, "trade_date": day,
              "candidate_owner_id": owner_id,
              "capture_observed_at": f"{day}T16:00:00+08:00"}
    contract_path = tmp_path / "config/limit_contract.json"
    contract = {"path": "config/limit_contract.json",
                "sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                "bytes": contract_path.stat().st_size}
    receipt = {"production_admission": False, "contract": contract,
        "owners": [{"trade_date": day, "artifact": limit,
                    "raw_binding": owner["raw"], "baostock_source": source,
                    "counts": {"rows": 0}}]}
    legacy.write_text(json.dumps(receipt), encoding="utf-8")

    artifact, row, selected_receipt, _ = stress._limit_owner(tmp_path, candidate, day)

    assert artifact == limit
    assert row["trade_date"] == day
    assert selected_receipt == legacy


def test_predecessor_core_avoids_inflating_unused_full_historical_universe(tmp_path, monkeypatch):
    day = "2026-03-03"
    core = _bind(tmp_path, "candidate/predecessor.jsonl.gz",
                 gzip.compress((json.dumps({"security_id": "SYN-1"}) + "\n").encode(), mtime=0))
    candidate = {"owners": {day: {"core": core}}}
    membership = {"path": "missing/historical_universe.jsonl.gz",
                  "sha256": "0" * 64, "bytes": 1}
    checked = []
    original = stress._checked

    def track(root, binding):
        checked.append(binding)
        return original(root, binding)

    monkeypatch.setattr(stress, "_checked", track)
    universe, source = stress._comparison_universe(tmp_path, candidate, day, membership)

    assert universe == {"SYN-1"}
    assert source == core
    assert checked == [core]


def test_historical_universe_remains_the_predecessor_fallback(tmp_path):
    day = "2026-03-03"
    membership = _bind(tmp_path, "historical_universe.jsonl.gz",
        gzip.compress(("\n".join(json.dumps(row) for row in [
            {"security_id": "SYN-IN", "trade_date": day, "board_scope": "SH_MAIN"},
            {"security_id": "SYN-OTHER-DATE", "trade_date": "2026-03-02", "board_scope": "SH_MAIN"},
            {"security_id": "SYN-OTHER-BOARD", "trade_date": day, "board_scope": "OTHER"},
        ]) + "\n").encode(), mtime=0))
    universe, source = stress._comparison_universe(tmp_path, {"owners": {}}, day, membership)
    assert universe == {"SYN-IN"}
    assert source == membership
