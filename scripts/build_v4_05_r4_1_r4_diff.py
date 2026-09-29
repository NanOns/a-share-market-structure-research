"""Compare frozen R4 business outputs with canonical-identity R4.1 rebuilds."""
from __future__ import annotations

from hashlib import sha256
import gzip
from itertools import zip_longest
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05"
OUT = REPORT / "V4_05_R4_1_R4_DIFF.json"


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def record_change(changes: list[dict], category: str, identity: str, field: str, old: object, new: object) -> None:
    changes.append({"category": category, "identity": identity, "field": field, "r4": old, "r4_1": new})


def compare_value_maps(old: dict, new: dict, *, category: str, changes: list[dict], projection) -> int:
    compared = 0
    old_seen: set[str] = set()
    new_seen: set[str] = set()
    old_iterator, new_iterator = iter_rows(old), iter_rows(new)
    for index, pair in enumerate(zip_longest(old_iterator, new_iterator)):
        old_row, new_row = pair
        if old_row is None or new_row is None:
            record_change(changes, category, "ROW_SET", f"row_count_at_{index}",
                          None if old_row is None else old_row.get("security_id"),
                          None if new_row is None else new_row.get("security_id"))
            continue
        sid = old_row["security_id"]
        if sid in old_seen or new_row["security_id"] in new_seen:
            raise ValueError(f"duplicate identity in {category} artifacts at row {index}")
        old_seen.add(sid)
        new_seen.add(new_row["security_id"])
        if sid != new_row["security_id"]:
            record_change(changes, category, sid, "row_order_identity", sid, new_row["security_id"])
        left, right = projection(old_row), projection(new_row)
        compared += 1
        if left != right:
            differing_fields = sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
            record_change(changes, category, sid, "business_projection_fields", differing_fields,
                          {"r4_sha256": sha256(json.dumps(left, sort_keys=True, ensure_ascii=False,
                                                         separators=(",", ":")).encode("utf-8")).hexdigest(),
                           "r4_1_sha256": sha256(json.dumps(right, sort_keys=True, ensure_ascii=False,
                                                           separators=(",", ":")).encode("utf-8")).hexdigest()})
    return compared


def target_snapshot_projection(value: dict) -> dict:
    result = {key: item for key, item in value.items()
              if key not in {"source_head_sha", "source_head_sha256", "source_head_hash_algorithm"}}
    result["start_universe_provenance"] = {
        horizon: {key: item for key, item in row.items()
                  if key not in {"source_head_sha", "source_head_hash_algorithm"}}
        for horizon, row in value.get("start_universe_provenance", {}).items()}
    return result


def primitive_quality_projection(rows: dict) -> dict:
    identity_fields = {"input_digest", "output_digest", "window_identity"}
    return {
        key: {name: value for name, value in item.items() if name not in identity_fields}
        for key, item in rows.items()
    }


def compare_r4_to_r4_1() -> dict:
    changes: list[dict] = []
    old_snapshot_path = REPORT / "V4_05_R4_TARGET_MARKET_SNAPSHOT.json"
    new_snapshot_path = REPORT / "V4_05_R4_1_TARGET_MARKET_SNAPSHOT.json"
    old_snapshot, new_snapshot = load_json(old_snapshot_path), load_json(new_snapshot_path)
    if target_snapshot_projection(old_snapshot) != target_snapshot_projection(new_snapshot):
        record_change(changes, "target_snapshot", "ALL", "business_projection",
                      target_snapshot_projection(old_snapshot), target_snapshot_projection(new_snapshot))

    old_ref, new_ref = load_json(REPORT / "V4_05_R4_MARKET_REFERENCE.json"), load_json(REPORT / "V4_05_R4_1_MARKET_REFERENCE.json")
    reference_projection = lambda value: {
        "target_trade_date": value["target_trade_date"],
        "market_calendar_id": value["market_calendar_id"],
        "target_market_snapshot_id": value["target_market_snapshot_id"],
        "target_adjustment_basis_id": value["target_adjustment_basis_id"],
        "max_source_trade_date": value["max_source_trade_date"],
        "horizons": {key: {field: row[field] for field in (
            "horizon_sessions", "start_session", "end_session", "start_universe_snapshot_id",
            "evaluable_set_identity", "adjustment_basis_id", "window_identity", "reference_return",
            "universe_count", "evaluable_count", "missing_count", "coverage", "quality_state",
            "unknown_reason", "max_source_trade_date", "historical_as_recorded_claim")}
            for key, row in value["horizons"].items()}
    }
    if reference_projection(old_ref) != reference_projection(new_ref):
        record_change(changes, "market_reference", "1/3/5", "business_projection",
                      reference_projection(old_ref), reference_projection(new_ref))

    old_factor = REPORT / "staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz"
    new_factor = REPORT / "staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz"
    factor_rows = compare_value_maps(old_factor, new_factor, category="factor", changes=changes,
        projection=lambda row: {"security_id": row["security_id"], "source_security_key": row["source_security_key"],
                                "board_scope": row["board_scope"], "trade_date": row["trade_date"],
                                "coordinate_basis": row["coordinate_basis"],
                                "fields": {key: {"value": item["value"], "quality_state": item["quality_state"],
                                                "unknown_reason": item.get("unknown_reason")}
                                           for key, item in row["fields"].items()}})

    old_profile = REPORT / "staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz"
    new_profile = REPORT / "staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz"
    profile_rows = compare_value_maps(old_profile, new_profile, category="core_profile_state", changes=changes,
        projection=lambda row: {"security_id": row["security_id"], "symbol": row["symbol"], "board": row["board"],
                                "trade_date": row["trade_date"], "coordinate_basis": row["coordinate_basis"],
                                "profile_quality": row["profile_quality"],
                                "profile_component_status": row["profile_component_status"],
                                "primitive_quality": primitive_quality_projection(row["primitive_quality"]),
                                "states": {key: {"value": item["value"], "unknown_reason": item.get("unknown_reason")}
                                           for key, item in row["states"].items()}})

    old_period = REPORT / "staging/V4_05_R4_PERIOD_ASOF.jsonl.gz"
    new_period = REPORT / "staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz"
    period_sha_old, period_sha_new = file_sha(old_period), file_sha(new_period)
    if period_sha_old != period_sha_new:
        old_rows, new_rows = read_rows(old_period), read_rows(new_period)
        if old_rows != new_rows:
            record_change(changes, "period", "ALL", "row_content", "R4 rows differ", "R4.1 rows differ")

    old_regime, new_regime = load_json(REPORT / "V4_05_R4_MARKET_REGIME.json"), load_json(REPORT / "V4_05_R4_1_MARKET_REGIME.json")
    regime_keys = ("trade_date", "breadth_axis", "participation_axis", "stress_level", "stress_change", "trend_axis")
    old_regime_business = {key: old_regime["target_row"][key] for key in regime_keys}
    new_regime_business = {key: new_regime["target_row"][key] for key in regime_keys}
    if old_regime_business != new_regime_business:
        record_change(changes, "market_regime", "2026-09-28", "target_axes", old_regime_business, new_regime_business)

    old_profile_receipt = load_json(REPORT / "V4_05_R4_CORE_PROFILE_REPLAY.json")
    new_profile_receipt = load_json(REPORT / "V4_05_R4_1_CORE_PROFILE_REPLAY.json")
    old_factor_receipt = load_json(REPORT / "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json")
    new_factor_receipt = load_json(REPORT / "V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json")
    old_identity = load_json(REPORT / "V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json")
    new_identity = load_json(REPORT / "V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json")
    old_period_receipt = load_json(REPORT / "V4_05_R4_PERIOD_ASOF.json")
    new_period_receipt = load_json(REPORT / "V4_05_R4_1_PERIOD_ASOF.json")

    r4_ids = {row["security_id"] for row in iter_rows(old_profile)}
    r4_1_ids = {row["security_id"] for row in iter_rows(new_profile)}
    state_change_count = sum(change["category"] == "core_profile_state" for change in changes)
    return {
        "contract_id": "V4_05_R4_1_R4_DIFF_V1",
        "status": "PASS" if not changes and r4_ids == r4_1_ids
                  and new_ref["target_trade_date"] == "2026-09-28"
                  and len(r4_1_ids) == 5222 and old_regime_business["trend_axis"] == "UNKNOWN"
                  and new_regime_business["trend_axis"] == "UNKNOWN" else "FAIL",
        "business_field_changes": sum(change["category"] != "core_profile_state" for change in changes), "state_changes": state_change_count,
        "unexpected_business_value_drift": len(changes), "change_samples": changes[:20],
        "target_trade_date": new_ref["target_trade_date"], "target_identities": len(new_snapshot["identities"]),
        "profile_row_set": {"r4": len(r4_ids), "r4_1": len(r4_1_ids), "same_id_set": r4_ids == r4_1_ids},
        "factor_business_rows_compared": factor_rows, "core_profile_state_rows_compared": profile_rows,
        "frozen_values": {
            "market_reference_1_3_5": {key: new_ref["horizons"][key]["reference_return"] for key in ("1", "3", "5")},
            "period_rows": {"r4": old_period_receipt["row_count"], "r4_1": new_period_receipt["row_count"],
                            "artifact_sha256_equal": period_sha_old == period_sha_new,
                            "r4_sha256": period_sha_old, "r4_1_sha256": period_sha_new},
            "factor_logical_digest": {"r4": old_factor_receipt["logical_digest"], "r4_1": new_factor_receipt["logical_digest"],
                                      "business_values_equal": len(changes) == 0},
            "core_profile_logical_digest": {"r4": old_profile_receipt["logical_digest"], "r4_1": new_profile_receipt["logical_digest"],
                                            "state_values_equal": len(changes) == 0},
            "market_snapshot_id": {"r4": old_identity["target_market_snapshot_id"],
                                   "r4_1": new_identity["target_market_snapshot_id"],
                                   "equal": old_identity["target_market_snapshot_id"] == new_identity["target_market_snapshot_id"]},
            "market_regime_trend_axis": {"r4": old_regime_business["trend_axis"], "r4_1": new_regime_business["trend_axis"]},
        },
        "allowed_identity_rebinds": {
            "go_forward_head_identity": {"r4": old_snapshot["source_head_sha256"], "r4_1": new_snapshot["source_head_sha256"]},
            "market_reference_input_source_digest": {"r4": old_ref["horizons"]["1"]["input_source_digest"],
                                                     "r4_1": new_ref["horizons"]["1"]["input_source_digest"]},
            "market_regime_input_source_digest": {"r4": old_regime["identity"]["input_source_digest"],
                                                  "r4_1": new_regime["identity"]["input_source_digest"]},
            "factor_market_reference_hash": {"r4": old_factor_receipt["market_reference_sha256"],
                                              "r4_1": new_factor_receipt["market_reference_sha256"]},
            "core_profile_source_digest": {"r4": old_profile_receipt["source_digest"],
                                            "r4_1": new_profile_receipt["source_digest"]},
        },
        "artifacts": {
            str(path.relative_to(ROOT).as_posix()): {"sha256": file_sha(path), "byte_count": path.stat().st_size}
            for path in (new_period, REPORT / "V4_05_R4_1_TARGET_MARKET_SNAPSHOT.json",
                         REPORT / "V4_05_R4_1_MARKET_REFERENCE.json", REPORT / "V4_05_R4_1_MARKET_REGIME.json",
                         REPORT / "staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz", new_profile)
        },
        "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE",
                         "acceptance_result": "PASS" if not changes else "FAIL",
                         "evidence": "R4.1 rebuilds retain all frozen R4 business values and state values; only canonical source/output lineage identities rebind.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1"},
    }


def main() -> dict:
    result = compare_r4_to_r4_1()
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, OUT)
    return result


if __name__ == "__main__":
    result = main()
    print(json.dumps({"status": result["status"], "unexpected_business_value_drift": result["unexpected_business_value_drift"],
                      "profile_row_set": result["profile_row_set"], "market_reference_1_3_5": result["frozen_values"]["market_reference_1_3_5"]},
                     ensure_ascii=False, sort_keys=True))
